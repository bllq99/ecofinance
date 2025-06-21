from django.shortcuts import render, redirect, get_object_or_404
from .models import Transaccion, ObjetivoAhorro, Presupuesto, SerieRecurrente
from .forms import TransaccionForm, ObjetivoForm, PresupuestoForm
from django.db.models import Sum
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta, date
from django.utils import timezone
from itertools import groupby
from django.utils.timezone import localtime, now
from django.contrib.auth.decorators import login_required
from django.utils.formats import number_format
import json
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse, HttpResponse
import csv
from django.utils.encoding import smart_str
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from django.db.models.functions import TruncDay, TruncMonth
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from dateutil.relativedelta import relativedelta
from openpyxl import Workbook
from io import BytesIO
from django.core.mail import EmailMessage, send_mail
from .openai_utils import obtener_recomendaciones
from django.conf import settings


# 🏠 Dashboard: muestra resumen de ingresos, gastos y objetivos
@login_required
def dashboard(request):
    # --- Notificaciones de objetivos por vencer ---
    email_enabled = request.session.get('email_notifications', True)
    goal_updates_enabled = request.session.get('goal_updates_notifications', False)

    if email_enabled and goal_updates_enabled:
        hoy = timezone.now().date()
        limite_vencimiento = hoy + timedelta(days=7)
        
        # Objetivos que están por vencer en los próximos 7 días y no están completados
        objetivos_por_vencer = ObjetivoAhorro.objects.filter(
            usuario=request.user,
            fecha_limite__gte=hoy,
            fecha_limite__lte=limite_vencimiento,
            completado=False
        )

        # Usar la sesión para evitar enviar notificaciones repetidas
        notificaciones_enviadas = request.session.get('notif_vencimiento_enviadas', [])
        
        for objetivo in objetivos_por_vencer:
            if objetivo.id not in notificaciones_enviadas:
                send_mail(
                    'Tu Objetivo de Ahorro está por Vencer',
                    f"Hola {request.user.first_name or request.user.username},\n\n"
                    f"¡Atención! Tu objetivo '{objetivo.nombre}' está a punto de vencer el {objetivo.fecha_limite.strftime('%d/%m/%Y')}.\n\n"
                    "Asegúrate de hacer tus últimos aportes para alcanzar tu meta.\n\n"
                    "El equipo de EcoFinance",
                    settings.DEFAULT_FROM_EMAIL,
                    [request.user.email]
                )
                notificaciones_enviadas.append(objetivo.id)
        
        request.session['notif_vencimiento_enviadas'] = notificaciones_enviadas

    # Generar transacciones recurrentes hasta hoy antes de mostrar el dashboard
    generar_transacciones_recurrentes(request.user, date.today(), date.today())

    fecha_actual = timezone.now().date()
    
    # Obtener mes y año del parámetro mes_anio en formato YYYY-MM
    mes_anio_str = request.GET.get('mes_anio')

    # Inicializar mes y año para el filtro y para pasar al contexto
    mes_para_filtro = fecha_actual.month
    anio_para_filtro = fecha_actual.year

    if mes_anio_str:
        try:
            # Intentar parsear la cadena YYYY-MM
            fecha_seleccionada = datetime.strptime(mes_anio_str, '%Y-%m').date()
            mes_para_filtro = fecha_seleccionada.month
            anio_para_filtro = fecha_seleccionada.year
        except ValueError:
            pass

    # Filtrar transacciones por el mes y año seleccionados
    ingresos = Transaccion.objects.filter(
        usuario=request.user,
        tipo='INGRESO', 
        fecha__year=anio_para_filtro,
        fecha__month=mes_para_filtro
    ).exclude(descripcion="Balance Inicial").aggregate(Sum('monto'))['monto__sum'] or 0
    
    gastos = Transaccion.objects.filter(
        usuario=request.user,
        tipo='GASTO',
        fecha__year=anio_para_filtro,
        fecha__month=mes_para_filtro
    ).aggregate(Sum('monto'))['monto__sum'] or 0

    # Obtener gastos por categoría del mes y año seleccionados (usando mes_para_filtro y anio_para_filtro)
    gastos_por_categoria = Transaccion.objects.filter(
        usuario=request.user,
        tipo='GASTO',
        fecha__year=anio_para_filtro,
        fecha__month=mes_para_filtro
    ).values('categoria').annotate(
        total=Sum('monto')
    ).order_by('-total')

    # Obtener ingresos por categoría del mes y año seleccionados (usando mes_para_filtro y anio_para_filtro)
    ingresos_por_categoria = Transaccion.objects.filter(
        usuario=request.user,
        tipo='INGRESO',
        fecha__year=anio_para_filtro,
        fecha__month=mes_para_filtro
    ).exclude(descripcion="Balance Inicial").values('categoria').annotate(
        total=Sum('monto')
    ).order_by('-total')
    
    # Convertir a lista de diccionarios con categoría y monto para gastos
    gastos_categorias = [
        {
            'categoria': item['categoria'] if item['categoria'] else 'Sin categoría',
            'monto': float(item['total'])
        }
        for item in gastos_por_categoria
    ]

    # Convertir a lista de diccionarios con categoría y monto para ingresos
    ingresos_categorias = [
        {
            'categoria': item['categoria'] if item['categoria'] else 'Sin categoría',
            'monto': float(item['total'])
        }
        for item in ingresos_por_categoria
    ]

    # Serializar los datos usando json.dumps con ensure_ascii=False para manejar caracteres especiales
    gastos_categorias_json = json.dumps(gastos_categorias, ensure_ascii=False)
    ingresos_categorias_json = json.dumps(ingresos_categorias, ensure_ascii=False)

    balance = float(ingresos - gastos) # Este es el balance DEL MES seleccionado

    # Calcular el saldo total acumulado (independiente del filtro de mes/año)
    ingresos_totales_acumulado = Transaccion.objects.filter(
        usuario=request.user,
        tipo='INGRESO'
    ).aggregate(Sum('monto'))['monto__sum'] or 0

    gastos_totales_acumulado = Transaccion.objects.filter(
        usuario=request.user,
        tipo='GASTO'
    ).aggregate(Sum('monto'))['monto__sum'] or 0

    saldo_total = float(ingresos_totales_acumulado - gastos_totales_acumulado)

    hoy = timezone.now().date()

    # Definir diccionario para traducir meses al español
    meses_espanol = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    # Obtener transacciones registradas para el mes y año seleccionados hasta hoy
    transacciones_registradas = Transaccion.objects.filter(
        usuario=request.user,
        fecha__year=anio_para_filtro,
        fecha__month=mes_para_filtro,
        fecha__lte=hoy
    )

    # Obtener datos para el gráfico de gastos por día para el mes y año seleccionados
    gastos_dia = (
        Transaccion.objects
        .filter(usuario=request.user, tipo='GASTO', fecha__year=anio_para_filtro, fecha__month=mes_para_filtro, fecha__lte=hoy)
        .annotate(dia=TruncDay('fecha'))
        .values('dia')
        .annotate(total=Sum('monto'))
        .order_by('dia')
    )

    gastos_dias_labels = []
    gastos_dias_data = []
    for gasto in gastos_dia:
        gastos_dias_labels.append(gasto['dia'].strftime('%d/%m'))
        gastos_dias_data.append(float(gasto['total']))

    # Obtener datos para el gráfico de gastos por mes (últimos 3 meses con transacciones)
    # Filtrar gastos de los últimos 3 meses
    fecha_hace_tres_meses = hoy - relativedelta(months=3)
    gastos_mes_query = (
        Transaccion.objects
        .filter(usuario=request.user, tipo='GASTO', fecha__gte=fecha_hace_tres_meses, fecha__lte=hoy)
        .annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(total=Sum('monto'))
        .order_by('mes')
    )

    meses_gastos = []
    gastos_por_mes = []
    max_gasto = 0
    mes_max_gasto = ""

    for gasto in gastos_mes_query:
        if gasto['mes'] is not None:
            mes_num = gasto['mes'].month
            anio_num = gasto['mes'].year
            mes_es = meses_espanol.get(mes_num, str(mes_num))
            mes_formateado = f"{mes_es} {anio_num}"
            meses_gastos.append(mes_formateado)
            monto = float(gasto['total'])
            gastos_por_mes.append(monto)
            if monto > max_gasto:
                max_gasto = monto
                mes_max_gasto = mes_formateado

    # Asegurarse de que las listas de meses y gastos por mes tengan el mismo tamaño para el gráfico
    # y que estén en el orden correcto.
    # La consulta ya ordena por mes, así que solo necesitamos formatear.

    # Si no hay gastos en los últimos 3 meses, puedes ajustar esto para mostrar un mensaje en el gráfico

    # Obtener series recurrentes activas cuya próxima fecha sea hoy
    series_recurrentes_hoy = []
    series_activas = SerieRecurrente.objects.filter(
        usuario=request.user,
        activa=True,
        transaccion__fecha_inicio__lte=hoy # Considerar solo series que empezaron antes o hoy
    ).prefetch_related(
        'transaccion_set'
    ).distinct()

    for serie in series_activas:
        trans_base = serie.transaccion_set.filter(es_recurrente=True).first()
        if trans_base:
            # Calcular próxima fecha (lógica similar a lista_transacciones)
            proxima_fecha = trans_base.fecha_inicio
            dias_desde_inicio = (hoy - trans_base.fecha_inicio).days # Usar hoy para calcular desde el inicio

            if dias_desde_inicio >= 0:
                 if trans_base.periodicidad == 'DIARIA':
                     proxima_fecha = trans_base.fecha_inicio + timedelta(days=dias_desde_inicio + 1)
                 elif trans_base.periodicidad == 'SEMANAL':
                     semanas = dias_desde_inicio // 7 + 1
                     proxima_fecha = trans_base.fecha_inicio + timedelta(weeks=semanas)
                 elif trans_base.periodicidad == 'MENSUAL':
                     meses_diff = (hoy.year - trans_base.fecha_inicio.year) * 12 + hoy.month - trans_base.fecha_inicio.month
                     if hoy.day < trans_base.fecha_inicio.day:
                          meses_diff -= 1
                     next_month_num = trans_base.fecha_inicio.month + meses_diff + 1
                     next_year = trans_base.fecha_inicio.year + (next_month_num - 1) // 12
                     next_month = (next_month_num - 1) % 12 + 1
                     try:
                         proxima_fecha = trans_base.fecha_inicio.replace(year=next_year, month=next_month)
                     except ValueError:
                         proxima_fecha = trans_base.fecha_inicio.replace(year=next_year, month=next_month, day=1) + relativedelta(months=1) - timedelta(days=1)
                 elif trans_base.periodicidad == 'ANUAL':
                     años_pasados = hoy.year - trans_base.fecha_inicio.year
                     if hoy < trans_base.fecha_inicio.replace(year=hoy.year):
                         años_pasados -= 1
                     proxima_fecha = trans_base.fecha_inicio + relativedelta(years=años_pasados + 1)
                 else:
                     proxima_fecha = None # Periodicidad no reconocida o futura
            else:
                 proxima_fecha = trans_base.fecha_inicio # Si la fecha inicio es futura, la proxima es la fecha inicio

            # Verificar que la próxima fecha no exceda la fecha fin si existe y que sea hoy
            if proxima_fecha and proxima_fecha == hoy and (trans_base.fecha_fin is None or proxima_fecha <= trans_base.fecha_fin):
                # Crear una representación de la transacción recurrente para hoy
                series_recurrentes_hoy.append({
                    'descripcion': trans_base.descripcion,
                    'monto': trans_base.monto,
                    'tipo': trans_base.tipo,
                    'fecha': hoy, # La fecha es hoy
                    'categoria': trans_base.categoria,
                    'es_recurrente': True, # Marcar como recurrente
                    'id': f'rec_{serie.id}_{hoy.strftime('%Y%m%d')}' # ID único para la plantilla
                })

    # Combinar transacciones registradas y recurrentes de hoy
    ultimas_transacciones_combinadas = list(transacciones_registradas) + series_recurrentes_hoy

    # Ordenar la lista combinada por fecha descendente, y luego por un identificador
    # Usar isinstance para diferenciar entre objetos Transaccion y diccionarios
    ultimas_transacciones_combinadas.sort(key=lambda x: (
        x.fecha if isinstance(x, Transaccion) else x.get('fecha'),
        x.id if isinstance(x, Transaccion) else x.get('id', 0) # Usar 0 o un valor similar como default si el id no existe en el dict
    ), reverse=True)

    # Obtener las últimas 10 transacciones de la lista combinada
    ultimas_transacciones_final = ultimas_transacciones_combinadas[:10]
    
    # Obtener objetivos y calcular días restantes
    objetivos = ObjetivoAhorro.objects.filter(usuario=request.user)
    colores = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']  # Lista de colores predefinidos
    for idx, objetivo in enumerate(objetivos):
        progreso = (float(objetivo.monto_actual) / float(objetivo.monto_objetivo) * 100) if objetivo.monto_objetivo > 0 else 0
        objetivo.progreso = round(progreso, 1)
        objetivo.progreso_str = f"{objetivo.progreso:.1f}"  # Formatear a un decimal
        objetivo.color = colores[idx % len(colores)]  # Asignar color dinámico basado en la posición
    objetivos_por_vencer = []
    objetivos_vencidos = []
    
    # Preparar datos para el gráfico de ahorro
    objetivos_ahorro = []
    total_ahorrado = 0
    
    for objetivo in objetivos:
        # Calcular el progreso
        progreso = (float(objetivo.monto_actual) / float(objetivo.monto_objetivo) * 100) if objetivo.monto_objetivo > 0 else 0
        # objetivo.progreso = f"{progreso:.1f}"  # Formato con punto decimal
        # Agregar datos para el gráfico
        objetivos_ahorro.append({
            'nombre': objetivo.nombre,
            'monto_actual': float(objetivo.monto_actual),
            'monto_objetivo': float(objetivo.monto_objetivo),
            'progreso': round(progreso, 1)
        })
        total_ahorrado += float(objetivo.monto_actual)
        
        if objetivo.fecha_limite:
            dias_restantes = (objetivo.fecha_limite - fecha_actual).days
            if dias_restantes <= 10 and dias_restantes >= 0:
                objetivos_por_vencer.append({
                    'nombre': objetivo.nombre,
                    'dias_restantes': dias_restantes,
                    'progreso': round(progreso, 1)
                })
            elif dias_restantes < 0:
                objetivos_vencidos.append({
                    'nombre': objetivo.nombre,
                    'dias_vencido': abs(dias_restantes),
                    'progreso': round(progreso, 1)
                })
        
        # Agregar el progreso al objeto objetivo para usarlo en el template
        objetivo.progreso = round(progreso, 1)
        objetivo.progreso_str = f"{objetivo.progreso:.1f}"  # Formatear a un decimal
    
    # Obtener el último presupuesto del usuario
    presupuesto = Presupuesto.objects.filter(usuario=request.user).last()
    presupuesto_monto = float(presupuesto.monto) if presupuesto else 0

    # Obtener la lista de meses y años con transacciones para los filtros
    # Excluir valores nulos de mes
    meses_anios_con_transacciones = Transaccion.objects.filter(usuario=request.user).exclude(fecha__isnull=True).annotate(
        mes=TruncMonth('fecha')
    ).values_list('mes', flat=True).distinct().order_by('mes')

    # Formatear los meses y años para el selector
    meses_anios_formateados = []
    for mes_anio in meses_anios_con_transacciones:
        if mes_anio:
            mes_num = mes_anio.month
            anio_num = mes_anio.year
            # Usar el diccionario con claves numéricas para formatear el texto
            mes_es = meses_espanol.get(mes_num, str(mes_num)) # Usar número de mes como clave
            meses_anios_formateados.append({'value': f'{anio_num}-{mes_num:02d}', 'text': f'{mes_es} {anio_num}'})

    nombre_usuario = request.user.first_name or request.user.username

    # ¿El usuario tiene alguna transacción registrada?
    tiene_transacciones = Transaccion.objects.filter(usuario=request.user).exists()

    # Preparar el contexto para el template
    context = {
        'ingresos': float(ingresos),
        'gastos': float(gastos),
        'saldo_total': saldo_total,
        'ultimas_transacciones': ultimas_transacciones_final,
        'meses_anios': meses_anios_formateados,
        'mes_seleccionado': mes_para_filtro,
        'anio_seleccionado': anio_para_filtro,
        'gastos_categorias': gastos_categorias,  # Pasar los datos sin serializar
        'ingresos_categorias': ingresos_categorias,  # Pasar los datos sin serializar
        'objetivos': objetivos,
        'presupuesto': presupuesto_monto,
        'objetivos_por_vencer': objetivos_por_vencer,
        'objetivos_vencidos': objetivos_vencidos,
        'objetivos_ahorro': objetivos_ahorro,  # Pasar los datos sin serializar
        'total_ahorrado': float(total_ahorrado),
        'gastos_dias_labels': gastos_dias_labels,
        'gastos_dias_data': gastos_dias_data,
        'meses_gastos': meses_gastos,
        'gastos_por_mes': gastos_por_mes,
        'mes_max_gasto': mes_max_gasto,
        'max_gasto': max_gasto,
        'nombre_usuario': nombre_usuario,
        'tiene_transacciones': tiene_transacciones,
    }

    return render(request, 'finanzas/dashboard.html', context)


# 📄 Lista de transacciones
@login_required
def lista_transacciones(request):
    fecha_actual = timezone.now().date()

    # Obtener parámetros de filtro
    mes = request.GET.get('mes')
    categoria = request.GET.get('categoria')
    fecha_desde_str = request.GET.get('fecha_desde')
    fecha_hasta_str = request.GET.get('fecha_hasta')
    orden = request.GET.get('orden')
    orden_recurrente = request.GET.get('orden_recurrente')

    # Convertir la cadena 'None' a None real para los parámetros recibidos
    if mes == 'None':
        mes = None
    if categoria == 'None':
        categoria = None
    if fecha_desde_str == 'None':
        fecha_desde_str = None
    if fecha_hasta_str == 'None':
        fecha_hasta_str = None
    if orden == 'None':
        orden = None

    fecha_desde_filtro = None
    fecha_hasta_filtro = None

    # Convertir fechas de string a date objects para el filtro
    if fecha_desde_str:
        try:
            fecha_desde_filtro = datetime.strptime(fecha_desde_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    if fecha_hasta_str:
        try:
            fecha_hasta_filtro = datetime.strptime(fecha_hasta_str, '%Y-%m-%d').date()
        except ValueError:
            pass

    # Filtrar transacciones para la tabla principal
    transacciones = Transaccion.objects.filter(
        usuario=request.user,
        fecha__lte=fecha_actual # Añadir filtro para mostrar solo transacciones hasta la fecha actual
    )

    # Aplicar filtros
    if mes:
        # Si el mes viene en formato YYYY-MM, extraer solo el mes
        if isinstance(mes, str) and '-' in mes:
            try:
                # Intentar convertir la cadena YYYY-MM a un objeto date para extraer el mes
                mes_date = datetime.strptime(mes, '%Y-%m').date()
                mes_num = mes_date.month
            except ValueError:
                # Si hay un error en el formato, no aplicar el filtro de mes
                mes_num = None
        else:
            # Si ya es solo el número del mes (o None/cadena vacía), usarlo directamente
            try:
                mes_num = int(mes)
            except (ValueError, TypeError):
                mes_num = None

        if mes_num is not None:
            transacciones = transacciones.filter(fecha__month=mes_num)
    if categoria:
        transacciones = transacciones.filter(categoria=categoria)
    if fecha_desde_filtro:
        transacciones = transacciones.filter(fecha__gte=fecha_desde_filtro)
    if fecha_hasta_filtro:
        transacciones = transacciones.filter(fecha__lte=fecha_hasta_filtro)

    # Orden por defecto: fecha descendente y luego id descendente
    if not orden:
        orden = '-fecha'
    if orden == '-fecha':
        ordenes = ['-fecha', '-id']
    elif orden == 'fecha':
        ordenes = ['fecha', 'id']
    elif orden == '-monto':
        ordenes = ['-monto', '-fecha', '-id']
    elif orden == 'monto':
        ordenes = ['monto', 'fecha', 'id']
    elif orden == 'descripcion':
        ordenes = ['descripcion', '-fecha', '-id']
    elif orden == '-descripcion':
        ordenes = ['-descripcion', '-fecha', '-id']
    elif orden == 'categoria':
        ordenes = ['categoria', '-fecha', '-id']
    elif orden == '-categoria':
        ordenes = ['-categoria', '-fecha', '-id']
    elif orden == 'tipo':
        ordenes = ['tipo', '-fecha', '-id']
    elif orden == '-tipo':
        ordenes = ['-tipo', '-fecha', '-id']
    else:
        ordenes = [orden, '-fecha', '-id']

    transacciones = transacciones.order_by(*ordenes)

    # Obtener categorías únicas para el filtro
    categorias = Transaccion.objects.filter(usuario=request.user).values_list('categoria', flat=True).distinct()
    # Remover valores None de categorías y ordenar
    categorias = sorted([cat for cat in categorias if cat is not None])

    # Obtener meses únicos de transacciones para el filtro (formato 'YYYY-MM')
    meses_con_transacciones = Transaccion.objects.filter(usuario=request.user).annotate(mes_anio=TruncMonth('fecha')).values_list('mes_anio', flat=True).distinct().order_by('mes_anio')

    # Formatear los meses para mostrar en el selector (ej: 'Enero 2025')
    meses_formateados = []
    # Diccionario para traducir meses al español
    meses_espanol = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    for mes_anio_date in meses_con_transacciones:
        if mes_anio_date:
            mes_num = mes_anio_date.month
            anio_num = mes_anio_date.year
            meses_formateados.append({'value': f'{anio_num}-{mes_num:02d}', 'text': f'{meses_espanol[mes_num]} {anio_num}'})

    # Paginación
    page = request.GET.get('page', 1)
    paginator = Paginator(transacciones, 10)
    try:
        transacciones_paginadas = paginator.page(page)
    except PageNotAnInteger:
        transacciones_paginadas = paginator.page(1)
    except EmptyPage:
        transacciones_paginadas = paginator.page(paginator.num_pages)

    # Obtener series recurrentes activas con sus transacciones base en una sola consulta
    series_con_base = []
    series_activas = SerieRecurrente.objects.filter(
        usuario=request.user,
        activa=True
    ).prefetch_related(
        'transaccion_set'
    )

    # Mapeo de valores de periodicidad a texto legible
    PERIODICIDAD_DISPLAY = {
        'DIARIA': 'Diaria',
        'SEMANAL': 'Semanal',
        'MENSUAL': 'Mensual',
        'ANUAL': 'Anual',
    }

    for serie in series_activas:
        trans_base = serie.transaccion_set.filter(es_recurrente=True).first()
        if trans_base:
            # Buscar la última transacción generada para esta serie
            ultima_trans = serie.transaccion_set.filter(es_recurrente=True, fecha__lte=fecha_actual).order_by('-fecha').first()
            if ultima_trans:
                ultima_fecha = ultima_trans.fecha
            else:
                ultima_fecha = trans_base.fecha_inicio

            # Calcular la próxima fecha según la periodicidad
            if trans_base.periodicidad == 'DIARIA':
                proxima_fecha = ultima_fecha + timedelta(days=1)
            elif trans_base.periodicidad == 'SEMANAL':
                proxima_fecha = ultima_fecha + timedelta(weeks=1)
            elif trans_base.periodicidad == 'MENSUAL':
                proxima_fecha = ultima_fecha + relativedelta(months=1)
            elif trans_base.periodicidad == 'ANUAL':
                proxima_fecha = ultima_fecha + relativedelta(years=1)
            else:
                proxima_fecha = None

            # Verificar que la próxima fecha no exceda la fecha fin si existe
            if trans_base.fecha_fin and proxima_fecha and proxima_fecha > trans_base.fecha_fin:
                proxima_fecha = None

            # Obtener el texto legible de la periodicidad
            periodicidad_display = PERIODICIDAD_DISPLAY.get(trans_base.periodicidad, trans_base.periodicidad)

            series_con_base.append({
                'serie': serie,
                'trans': trans_base,
                'proxima_fecha': proxima_fecha,
                'periodicidad_display': periodicidad_display # Añadir el texto legible
            })

    # Lógica de ordenamiento para series recurrentes
    if orden_recurrente:
        def get_sort_key(item):
            # Obtener el campo base para ordenar (eliminar el signo menos si existe)
            campo = orden_recurrente.lstrip('-')
            trans_base = item['trans']

            # Mapear los nombres de columna de la plantilla a los campos del modelo/diccionario
            if campo == 'Descripción':
                return trans_base.descripcion
            elif campo == 'Categoría':
                return trans_base.categoria or '' # Usar cadena vacía para None
            elif campo == 'Tipo':
                return trans_base.tipo
            elif campo == 'Fecha Inicio':
                return trans_base.fecha_inicio
            elif campo == 'Fecha Fin':
                if trans_base.fecha_fin is None:
                    return date.max
                return trans_base.fecha_fin
            elif campo == 'Periodicidad':
                # Usar el texto legible para ordenar si está disponible
                return item.get('periodicidad_display', trans_base.periodicidad)
            elif campo == 'Próxima Fecha':
                if item['proxima_fecha'] is None:
                    return date.max
                return item['proxima_fecha']
            elif campo == 'Activa':
                return item['serie'].activa
            # Añadir otros campos si es necesario ordenar por ellos
            return getattr(trans_base, campo, None) # Fallback por si el campo no está mapeado

        # Determinar si el orden es descendente
        reverse_order = orden_recurrente.startswith('-')

        # Ordenar la lista
        series_con_base = sorted(series_con_base, key=get_sort_key, reverse=reverse_order)

    context = {
        'transacciones': transacciones_paginadas,
        'orden_actual': orden,
        'categorias': categorias,
        'meses': meses_formateados, # Pasar la lista de meses formateados
        'mes_actual': mes,
        'categoria_actual': categoria,
        'fecha_desde': fecha_desde_str,
        'fecha_hasta': fecha_hasta_str,
        'series_con_base': series_con_base,
        'today': fecha_actual,
        'orden_recurrente_actual': orden_recurrente,
    }

    return render(request, 'finanzas/lista_transacciones.html', context)


# ➕ Crear nueva transacción
@login_required
def nueva_transaccion(request):
    if request.method == 'POST':
        form = TransaccionForm(request.POST)
        if form.is_valid():
            transaccion = form.save(commit=False)
            transaccion.usuario = request.user
            tipo = request.POST.get('tipo')
            if tipo:
                transaccion.tipo = tipo

            # Si es recurrente, crear la serie recurrente si no existe
            if transaccion.es_recurrente:
                serie = SerieRecurrente.objects.create(
                    usuario=request.user,
                    activa=True
                )
                transaccion.serie_recurrente = serie

            transaccion.save()
            
            messages.success(request, '¡Transacción registrada exitosamente!')
            return redirect('dashboard')
    else:
        form = TransaccionForm()
    
    return render(request, 'finanzas/nueva_transaccion.html', {'form': form})

def calcular_saldo_total(usuario):
    ingresos_totales = Transaccion.objects.filter(
        usuario=usuario,
        tipo='INGRESO'
    ).aggregate(Sum('monto'))['monto__sum'] or 0

    gastos_totales = Transaccion.objects.filter(
        usuario=usuario,
        tipo='GASTO'
    ).aggregate(Sum('monto'))['monto__sum'] or 0

    return float(ingresos_totales - gastos_totales)


# 📄 Lista de objetivos de ahorro
@login_required
def lista_objetivos(request):
    objetivos = ObjetivoAhorro.objects.filter(usuario=request.user).order_by('fecha_limite')
    objetivos_por_vencer = []
    objetivos_vencidos = []
    fecha_actual = timezone.now().date()
    
    for objetivo in objetivos:
        # Calcular el progreso
        progreso = (objetivo.monto_actual / objetivo.monto_objetivo * 100) if objetivo.monto_objetivo > 0 else 0
        objetivo.progreso = round(progreso, 1)
        
        if objetivo.fecha_limite:
            dias_restantes = (objetivo.fecha_limite - fecha_actual).days
            if dias_restantes <= 10 and dias_restantes >= 0:
                objetivos_por_vencer.append({
                    'nombre': objetivo.nombre,
                    'dias_restantes': dias_restantes,
                    'progreso': objetivo.progreso
                })
            elif dias_restantes < 0:
                objetivos_vencidos.append({
                    'nombre': objetivo.nombre,
                    'dias_vencido': abs(dias_restantes),
                    'progreso': objetivo.progreso
                })
        objetivo.progreso_str = f"{objetivo.progreso:.1f}"  # Formatear a un decimal
    
    return render(request, 'finanzas/lista_objetivos.html', {
        'objetivos': objetivos,
        'objetivos_por_vencer': objetivos_por_vencer,
        'objetivos_vencidos': objetivos_vencidos,
        'fecha_actual': fecha_actual
    })


# ➕ Crear nuevo objetivo de ahorro
@login_required
def nuevo_objetivo(request):
    if request.method == 'POST':
        form = ObjetivoForm(request.POST)
        if form.is_valid():
            objetivo = form.save(commit=False)
            objetivo.usuario = request.user
            objetivo.save()
            messages.success(request, f'¡Objetivo "{objetivo.nombre}" creado exitosamente!')

            # --- Envío de correo al crear un nuevo objetivo ---
            email_enabled = request.session.get('email_notifications', True)
            goal_updates_enabled = request.session.get('goal_updates_notifications', False)

            if email_enabled and goal_updates_enabled:
                send_mail(
                    'Has Creado un Nuevo Objetivo de Ahorro',
                    (
                        f"Hola {request.user.first_name or request.user.username},\n\n"
                        f"Has creado un nuevo objetivo: '{objetivo.nombre}'.\n"
                        f"Tu meta es alcanzar ${int(objetivo.monto_objetivo):,}".replace(',', '.') + f" antes del {objetivo.fecha_limite.strftime('%d/%m/%Y')}.\n\n"
                        "¡Mucha suerte! Estamos aquí para ayudarte a lograrlo.\n\n"
                        "El equipo de EcoFinance"
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [request.user.email]
                )

            return redirect('lista_objetivos')
    else:
        form = ObjetivoForm(initial={'monto_actual': 0})

    fecha_actual = now().date().isoformat()  # Formato YYYY-MM-DD
    return render(request, 'finanzas/nuevo_objetivo.html', {
        'form': form,
        'fecha_actual': fecha_actual
    })


@login_required
def editar_objetivo(request, objetivo_id):
    objetivo = get_object_or_404(ObjetivoAhorro, id=objetivo_id, usuario=request.user)
    
    if request.method == 'POST':
        form = ObjetivoForm(request.POST, instance=objetivo)
        if form.is_valid():
            form.save()
            messages.success(request, f'¡Objetivo "{objetivo.nombre}" actualizado exitosamente!')
            return redirect('lista_objetivos')
    else:
        form = ObjetivoForm(instance=objetivo)

    return render(request, 'finanzas/editar_objetivo.html', {
        'form': form,
        'objetivo': objetivo
    })


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            nombre = user.first_name if user.first_name else user.email
            messages.success(request, f'¡Bienvenido {nombre}! Has iniciado sesión correctamente.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Correo electrónico o contraseña incorrectos')
            return render(request, 'finanzas/login.html')
    
    return render(request, 'finanzas/login.html')


def registro_view(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            return render(request, 'finanzas/registro.html', {
                'error': 'Las contraseñas no coinciden'
            })

        # Verificar si el email ya está registrado
        if User.objects.filter(email=email).exists():
            return render(request, 'finanzas/registro.html', {
                'error': 'El correo electrónico ya está registrado'
            })

        try:
            user = User.objects.create_user(username=email, email=email, password=password1)
            user.first_name = nombre
            user.save()            
            # Usa authenticate antes de login para obtener el backend
            user = authenticate(request, username=email, password=password1)
            login(request, user)
            
            return redirect('dashboard')
        except Exception as e:
            return render(request, 'finanzas/registro.html', {
                'error': 'Error al crear el usuario. Por favor, inténtalo de nuevo. ' + str(e)
            })

    return render(request, 'finanzas/registro.html')


@login_required
def establecer_presupuesto(request):
    if request.method == 'POST':
        form = PresupuestoForm(request.POST)
        if form.is_valid():
            presupuesto = form.save(commit=False)
            presupuesto.usuario = request.user
            presupuesto.save()
            messages.success(request, 'Presupuesto establecido correctamente')
            return redirect('dashboard')
    else:
        form = PresupuestoForm()

    return render(request, 'finanzas/establecer_presupuesto.html', {
        'form': form
    })


@login_required
def eliminar_transaccion(request, id):
    transaccion = get_object_or_404(Transaccion, id=id, usuario=request.user)
    
    # Verificar si la transacción es un aporte a un objetivo de ahorro
    if transaccion.descripcion.startswith("Aporte al objetivo:"):
        # Extraer el nombre del objetivo desde la descripción
        nombre_objetivo = transaccion.descripcion.replace("Aporte al objetivo: ", "").strip()
        objetivo = ObjetivoAhorro.objects.filter(usuario=request.user, nombre=nombre_objetivo).first()
        
        if objetivo:
            # Restar el monto de la transacción al progreso del objetivo
            objetivo.monto_actual -= transaccion.monto
            if objetivo.monto_actual < 0:
                objetivo.monto_actual = 0  # Asegurarse de que no sea negativo
            objetivo.save()

    # Eliminar la transacción
    transaccion.delete()
    messages.success(request, "Transacción eliminada con éxito.")
    return redirect('lista_transacciones')


def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('login')


@login_required
def establecer_balance_inicial(request):
    # Verificar si ya existe un balance inicial
    if Transaccion.objects.filter(usuario=request.user, descripcion="Balance Inicial").exists():
        messages.error(request, 'Ya has establecido un balance inicial.')
        return redirect('dashboard')

    if request.method == 'POST':
        balance_inicial = request.POST.get('balance_inicial')
        try:
            # Validar que el balance inicial sea un número válido
            balance_inicial = float(balance_inicial)
            if balance_inicial < 0:
                messages.error(request, 'El balance inicial no puede ser negativo.')
                return redirect('dashboard')

            # Crear una transacción de tipo "INGRESO" para el balance inicial
            Transaccion.objects.create(
                usuario=request.user,
                descripcion="Balance Inicial",
                monto=balance_inicial,
                tipo="INGRESO",
                categoria="General",
                fecha=timezone.now()
            )

            messages.success(request, '¡Balance inicial establecido correctamente!')
            return redirect('dashboard')
        except ValueError:
            messages.error(request, 'Por favor, ingresa un número válido.')
            return redirect('dashboard')
    else:
        return JsonResponse({'error': 'Método no permitido'}, status=405)


@login_required
def añadir_dinero_objetivo(request, objetivo_id):
    objetivo = get_object_or_404(ObjetivoAhorro, id=objetivo_id, usuario=request.user)
    user = request.user

    # Verificar si las notificaciones están activadas en la sesión
    email_enabled = request.session.get('email_notifications', True)
    goal_updates_enabled = request.session.get('goal_updates_notifications', False)

    if request.method == 'POST':
        monto = request.POST.get('monto')
        try:
            monto = Decimal(monto)
            if monto <= 0:
                messages.error(request, 'El monto debe ser mayor que 0.')
                return redirect('lista_objetivos')

            if objetivo.monto_actual + monto > objetivo.monto_objetivo:
                messages.warning(request, 'No puedes añadir más dinero del que falta para alcanzar el objetivo.')
                return redirect('lista_objetivos')
            
            monto_previo = objetivo.monto_actual
            estaba_completado = objetivo.completado

            # Crear una transacción de tipo "GASTO"
            Transaccion.objects.create(
                usuario=request.user,
                descripcion=f"Aporte al objetivo: {objetivo.nombre}",
                monto=monto,
                tipo="GASTO",
                categoria="Ahorro",
                fecha=timezone.now()
            )

            # Añadir el monto al objetivo
            objetivo.monto_actual += monto
            objetivo.save()

            if not estaba_completado and objetivo.completado:
                messages.success(request, f'¡Felicidades! Has completado tu objetivo "{objetivo.nombre}".')
            else:
                messages.success(request, f'Se han añadido ${int(monto):,}'.replace(',', '.') + f' al objetivo "{objetivo.nombre}".')

            # --- Lógica de envío de correos ---
            if email_enabled and goal_updates_enabled:
                # 1. Correo de confirmación por añadir dinero (se envía siempre)
                send_mail(
                    'Aporte a tu Objetivo de Ahorro',
                    f"Hola {user.first_name or user.username},\n\nHas añadido ${int(monto):,}".replace(',', '.') + f" a tu objetivo '{objetivo.nombre}'.\n¡Sigue así!",
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email]
                )

                # 2. Correo si el objetivo se acaba de completar
                if not estaba_completado and objetivo.completado:
                    send_mail(
                        '¡Has Cumplido tu Objetivo!',
                        (
                            f"Hola {user.first_name or user.username},\n\n¡EXTRAORDINARIO! Has alcanzado el 100% de tu objetivo de ahorro '{objetivo.nombre}'.\n"
                            f"Has logrado tu meta de ${int(objetivo.monto_objetivo):,}".replace(',', '.') + ". ¡Estamos muy orgullosos de ti!\n\n"
                            "El equipo de EcoFinance"
                        ),
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email]
                    )
                # 3. Correo si el objetivo está cerca de completarse (y no está ya completado)
                elif not objetivo.completado:
                    porcentaje_actual = (objetivo.monto_actual / objetivo.monto_objetivo) * 100
                    porcentaje_previo = (monto_previo / objetivo.monto_objetivo) * 100

                    if porcentaje_actual >= 90 and porcentaje_previo < 90:
                        send_mail(
                            '¡Casi cumples tu objetivo!',
                            f"Hola {user.first_name or user.username},\n\n¡Felicidades! Estás a punto de alcanzar tu objetivo '{objetivo.nombre}'.\n"
                            f"Has completado más del {porcentaje_actual:.0f}% de tu meta. ¡Ya casi lo tienes!",
                            settings.DEFAULT_FROM_EMAIL,
                            [user.email]
                        )

                # 4. Correo si la fecha límite está cerca (y no se ha enviado antes)
                dias_restantes = (objetivo.fecha_limite - date.today()).days
                notificacion_deadline_enviada = request.session.get(f'deadline_notified_{objetivo.id}', False)

                if 0 <= dias_restantes < 10 and not notificacion_deadline_enviada and not objetivo.completado:
                    send_mail(
                        '¡Tu Objetivo Está por Vencer!',
                        (
                            f"Hola {user.first_name or user.username},\n\n"
                            f"¡Atención! A tu objetivo '{objetivo.nombre}' le quedan solo {dias_restantes} día(s) para su fecha límite.\n\n"
                            "¡No te rindas, estás muy cerca de lograrlo!\n\n"
                            "El equipo de EcoFinance"
                        ),
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email]
                    )
                    request.session[f'deadline_notified_{objetivo.id}'] = True

        except (ValueError, InvalidOperation):
            messages.error(request, 'El monto ingresado no es válido.')

    return redirect('lista_objetivos')

@login_required
def eliminar_dinero_objetivo(request, objetivo_id):
    objetivo = get_object_or_404(ObjetivoAhorro, id=objetivo_id, usuario=request.user)
    
    if request.method == 'POST':
        monto = request.POST.get('monto')
        try:
            monto = Decimal(monto)
            if monto <= 0:
                messages.error(request, 'El monto debe ser mayor que 0')
                return redirect('lista_objetivos')
            
            if monto > objetivo.monto_actual:
                messages.error(request, 'No puedes retirar más dinero del que tienes en el objetivo')
                return redirect('lista_objetivos')
            
            objetivo.monto_actual -= monto
            objetivo.save()
            messages.success(request, f'Se han retirado ${int(monto):,}'.replace(',', '.') + f' del objetivo "{objetivo.nombre}"')
        except (ValueError, InvalidOperation):
            messages.error(request, 'El monto ingresado no es válido')
    
    return redirect('lista_objetivos')

@login_required
def eliminar_objetivo(request, objetivo_id):
    objetivo = get_object_or_404(ObjetivoAhorro, id=objetivo_id, usuario=request.user)
    
    if request.method == 'POST':
        nombre_objetivo = objetivo.nombre
        user = request.user
        
        # Primero, preparamos el correo
        email_enabled = request.session.get('notifications_email', False)
        goal_updates_enabled = request.session.get('notifications_goals', False)

        if email_enabled and goal_updates_enabled:
            try:
                send_mail(
                    'Has Eliminado un Objetivo de Ahorro',
                    (
                        f"Hola {user.first_name or user.username},\n\n"
                        f"Has eliminado tu objetivo de ahorro: '{nombre_objetivo}'.\n\n"
                        "Si esto fue un error, puedes crear uno nuevo cuando quieras.\n\n"
                        "El equipo de EcoFinance"
                    ),
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False  # Lo ponemos en False para depuración
                )
            except Exception as e:
                # Si hay un error al enviar el correo, lo mostramos como un mensaje
                messages.error(request, f"No se pudo enviar el correo de notificación. Error: {e}")
        else:
            # Mensaje de diagnóstico si las notificaciones están desactivadas
            messages.warning(request, "El correo de notificación no se envió porque las notificaciones por correo para objetivos están desactivadas en tu perfil.")

        # Ahora, eliminamos el objetivo
        objetivo.delete()
        messages.success(request, f'El objetivo "{nombre_objetivo}" ha sido eliminado correctamente.')
        
        return redirect('lista_objetivos')

    # Si no es POST, simplemente renderizamos la página (aunque el modal se encarga)
    # o redirigimos. La redirección es más segura.
    return redirect('lista_objetivos')

@login_required
def descargar_transacciones(request):
    # Obtener todas las transacciones del usuario
    transacciones = Transaccion.objects.filter(usuario=request.user).order_by('-fecha')
    
    # Crear la respuesta HTTP con el archivo CSV
    response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    response['Content-Disposition'] = 'attachment; filename="transacciones.csv"'
    
    # Crear el escritor CSV con punto y coma como separador
    writer = csv.writer(response, delimiter=';')
    
    # Escribir la cabecera
    writer.writerow(['Fecha', 'Descripción', 'Categoría', 'Tipo', 'Monto'])
    
    # Escribir las transacciones
    for transaccion in transacciones:
        writer.writerow([
            transaccion.fecha.strftime('%d/%m/%Y'),
            smart_str(transaccion.descripcion),
            smart_str(transaccion.categoria or 'Sin categoría'),
            transaccion.tipo,
            f"${transaccion.monto:,.0f}".replace(',', '.')
        ])
    
    return response

@login_required
def descargar_transacciones_pdf(request):
    # Obtener todas las transacciones del usuario
    transacciones = Transaccion.objects.filter(usuario=request.user).order_by('-fecha')
    
    # Crear el buffer para el PDF
    buffer = BytesIO()
    
    # Crear el documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Estilos
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30
    )
    
    # Título
    elements.append(Paragraph("Historial de Transacciones", title_style))
    elements.append(Spacer(1, 20))
    
    # Preparar datos para la tabla
    data = [['Fecha', 'Descripción', 'Categoría', 'Tipo', 'Monto']]
    
    for transaccion in transacciones:
        data.append([
            transaccion.fecha.strftime('%d/%m/%Y'),
            transaccion.descripcion,
            transaccion.categoria or 'Sin categoría',
            transaccion.tipo,
            f"${transaccion.monto:,.0f}".replace(',', '.')
        ])
    
    # Crear la tabla
    table = Table(data)
    
    # Estilo de la tabla
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),  # Alinear montos a la derecha
    ])
    
    # Aplicar estilos alternados a las filas
    for i in range(1, len(data)):
        if i % 2 == 0:
            table_style.add('BACKGROUND', (0, i), (-1, i), colors.lightgrey)
    
    table.setStyle(table_style)
    elements.append(table)
    
    # Construir el PDF
    doc.build(elements)
    
    # Obtener el valor del buffer
    pdf = buffer.getvalue()
    buffer.close()
    
    # Crear la respuesta HTTP
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="transacciones.pdf"'
    response.write(pdf)
    
    return response

def generar_transacciones_recurrentes(usuario, desde, hasta):
    series = SerieRecurrente.objects.filter(
        usuario=usuario,
        activa=True,
        transaccion__fecha_inicio__lte=hasta
    ).distinct()

    for serie in series:
        trans_base = Transaccion.objects.filter(serie_recurrente=serie).order_by('fecha_inicio').first()
        if not trans_base:
            continue

        fecha_inicio = trans_base.fecha_inicio
        fecha_fin = trans_base.fecha_fin or hasta
        periodicidad = trans_base.periodicidad.lower()
        ultima = serie.ultima_generada or fecha_inicio

        # Determina el incremento
        incrementos = {
            'diaria': relativedelta(days=1),
            'semanal': relativedelta(weeks=1),
            'mensual': relativedelta(months=1),
            'anual': relativedelta(years=1),
        }
        incremento = incrementos.get(periodicidad)
        if not incremento:
            continue

        fecha_actual = ultima
        while fecha_actual <= hasta and fecha_actual <= fecha_fin:
            # ¿Ya existe la transacción para esta fecha?
            if not Transaccion.objects.filter(
                serie_recurrente=serie, fecha=fecha_actual
            ).exists():
                Transaccion.objects.create(
                    usuario=trans_base.usuario,
                    descripcion=trans_base.descripcion,
                    monto=trans_base.monto,
                    tipo=trans_base.tipo,
                    fecha=fecha_actual,
                    categoria=trans_base.categoria,
                    es_recurrente=True,
                    periodicidad=trans_base.periodicidad,
                    fecha_inicio=trans_base.fecha_inicio,
                    fecha_fin=trans_base.fecha_fin,
                    serie_recurrente=serie
                )
                serie.ultima_generada = fecha_actual
                serie.save(update_fields=['ultima_generada'])
            fecha_actual += incremento

@login_required
def listar_recurrentes(request):
    series = SerieRecurrente.objects.filter(usuario=request.user, activa=True)
    return render(request, 'finanzas/lista_recurrentes.html', {'series': series})

@login_required
def eliminar_recurrente(request, serie_id):
    serie = get_object_or_404(SerieRecurrente, id=serie_id, usuario=request.user, activa=True)
    hoy = timezone.now().date()
    Transaccion.objects.filter(serie_recurrente=serie, fecha__gt=hoy).delete()
    serie.activa = False
    serie.save()
    messages.success(request, "Transacción recurrente eliminada y futuras transacciones canceladas.")
    return redirect('lista_transacciones')

@login_required
def perfil_usuario(request):
    if request.method == 'POST':
        # Formulario para actualizar información personal
        if 'update_profile' in request.POST:
            nombre = request.POST.get('nombre')
            if nombre:
                request.user.first_name = nombre
                request.user.save()
                messages.success(request, 'Tu nombre ha sido actualizado correctamente.')
            return redirect('perfil_usuario')

        # Formulario para cambiar la contraseña
        elif 'update_password' in request.POST:
            password_errors = []
            password_actual = request.POST.get('password_actual')
            password_nueva = request.POST.get('password_nueva')
            password_confirmar = request.POST.get('password_confirmar')
            user = request.user

            if not all([password_actual, password_nueva, password_confirmar]):
                password_errors.append('Por favor, completa todos los campos.')
            else:
                if not user.check_password(password_actual):
                    password_errors.append('La contraseña actual es incorrecta.')
                if password_nueva != password_confirmar:
                    password_errors.append('Las nuevas contraseñas no coinciden.')
                if password_actual == password_nueva:
                    password_errors.append('La nueva contraseña no puede ser igual a la anterior.')
                
                try:
                    validate_password(password_nueva, user=user)
                except ValidationError as errors:
                    password_errors.extend(list(errors))

            if password_errors:
                return render(request, 'finanzas/perfil.html', {'password_errors': password_errors})

            # Si todas las validaciones pasan, cambiar la contraseña
            user.set_password(password_nueva)
            user.save()
            update_session_auth_hash(request, user)  # Mantener la sesión
            messages.success(request, 'Tu contraseña ha sido actualizada correctamente.')
            return redirect('perfil_usuario')
            
        # Formulario para preferencias de notificaciones
        elif 'update_notifications' in request.POST:
            # Obtener el estado anterior desde la sesión
            old_email_pref = request.session.get('email_notifications', True)

            # Obtener el nuevo estado desde el formulario
            new_email_pref = request.POST.get('email_notifications') == 'on'
            new_goal_pref = request.POST.get('goal_updates') == 'on'

            # Guardar el nuevo estado en la sesión
            request.session['email_notifications'] = new_email_pref
            request.session['goal_updates_notifications'] = new_goal_pref

            # Comprobar si el estado cambió para enviar correo
            if new_email_pref and not old_email_pref:
                # Enviar correo de activación
                asunto = 'Notificaciones Activadas'
                mensaje = f"Hola {request.user.first_name or request.user.username},\n\nHas activado las notificaciones por correo electrónico en EcoFinance."
                send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [request.user.email])
                messages.success(request, '¡Notificaciones activadas! Se ha enviado un correo de confirmación.')
            elif not new_email_pref and old_email_pref:
                # Enviar correo de desactivación
                asunto = 'Notificaciones Desactivadas'
                mensaje = f"Hola {request.user.first_name or request.user.username},\n\nHas desactivado las notificaciones por correo electrónico en EcoFinance."
                send_mail(asunto, mensaje, settings.DEFAULT_FROM_EMAIL, [request.user.email])
                messages.success(request, '¡Notificaciones desactivadas! Se ha enviado un correo de confirmación.')
            else:
                messages.success(request, 'Tus preferencias de notificación han sido guardadas.')

            return redirect('perfil_usuario')

        # Formulario para configuración de privacidad
        elif 'update_privacy' in request.POST:
            # Obtener el estado anterior desde la sesión
            old_share_data = request.session.get('share_anonymous_data', True)
            old_public_profile = request.session.get('public_profile', False)

            # Obtener el nuevo estado desde el formulario
            new_share_data = request.POST.get('share_anonymous_data') == 'on'
            new_public_profile = request.POST.get('public_profile') == 'on'

            # Guardar siempre el nuevo estado en la sesión
            request.session['share_anonymous_data'] = new_share_data
            request.session['public_profile'] = new_public_profile

            # Comprobar si hubo cambios
            if old_share_data == new_share_data and old_public_profile == new_public_profile:
                messages.info(request, 'No se han detectado cambios en la configuración de privacidad.')
            else:
                # Si hubo cambios, y las notificaciones están activas, enviar correo
                if request.session.get('email_notifications', True):
                    send_mail(
                        'Actualización de tu Configuración de Privacidad',
                        (
                            f"Hola {request.user.first_name or request.user.username},\n\n"
                            "Tu configuración de privacidad en EcoFinance ha sido actualizada.\n\n"
                            f" - Compartir datos anónimos: {'Activado' if new_share_data else 'Desactivado'}\n"
                            f" - Perfil público: {'Activado' if new_public_profile else 'Desactivado'}\n\n"
                            "El equipo de EcoFinance"
                        ),
                        settings.DEFAULT_FROM_EMAIL,
                        [request.user.email]
                    )
                    messages.success(request, 'Configuración de privacidad guardada. Se ha enviado un correo de confirmación.')
                else:
                    messages.success(request, 'Tu configuración de privacidad ha sido guardada.')
            
            return redirect('perfil_usuario')

    # Para peticiones GET, pasar el estado de la sesión a la plantilla
    context = {
        'notification_prefs': {
            'email_notifications': request.session.get('email_notifications', True),
            'goal_updates_notifications': request.session.get('goal_updates_notifications', False)
        },
        'privacy_prefs': {
            'share_anonymous_data': request.session.get('share_anonymous_data', True),
            'public_profile': request.session.get('public_profile', False)
        }
    }
    return render(request, 'finanzas/perfil.html', context)

def enviar_notificacion_transacciones(usuario):
    # Obtener el mes y año actuales
    ahora = timezone.now()
    mes = ahora.month
    anio = ahora.year

    # Generar el archivo Excel con todas las transacciones del mes
    excel_file = generar_excel_transacciones(usuario, mes, anio)

    # Crear el correo
    asunto = f"Transacciones del mes {ahora.strftime('%B %Y')}"
    mensaje = f"Hola {usuario.first_name},\n\nAdjunto encontrarás el archivo Excel con todas las transacciones del mes {ahora.strftime('%B %Y')}.\n\nSaludos,\nEcoFinance"
    email = EmailMessage(
        asunto,
        mensaje,
        to=[usuario.email]
    )

    # Adjuntar el archivo Excel
    email.attach(f"transacciones_{mes}_{anio}.xlsx", excel_file.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Enviar el correo
    email.send()

def generar_excel_transacciones(usuario, mes, anio):
    # Crear un libro de Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Transacciones del Mes"

    # Agregar encabezados
    ws.append(["Fecha", "Descripción", "Categoría", "Tipo", "Monto"])

    # Filtrar todas las transacciones para el mes y año seleccionados
    from .models import Transaccion
    transacciones = Transaccion.objects.filter(
        usuario=usuario,
        fecha__year=anio,
        fecha__month=mes
    ).order_by("fecha")

    # Agregar datos al archivo
    for transaccion in transacciones:
        ws.append([
            transaccion.fecha.strftime("%d/%m/%Y"),
            transaccion.descripcion,
            transaccion.categoria or "Sin categoría",
            transaccion.tipo,
            transaccion.monto
        ])

    # Guardar el archivo en memoria
    excel_file = BytesIO()
    wb.save(excel_file)
    excel_file.seek(0)

    return excel_file

@login_required
def enviar_transacciones_mes(request):
    try:
        enviar_notificacion_transacciones(request.user)
        return JsonResponse({"message": "Correo enviado exitosamente."})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@login_required
def generar_recomendaciones(request):
    # Obtener transacciones del mes actual
    fecha_actual = timezone.now().date()
    transacciones_mes = Transaccion.objects.filter(
        usuario=request.user,
        fecha__year=fecha_actual.year,
        fecha__month=fecha_actual.month
    ).values('fecha', 'descripcion', 'categoria', 'tipo', 'monto')

    # Generar recomendaciones usando OpenAI
    recomendaciones = obtener_recomendaciones(transacciones_mes)

    return JsonResponse({'recomendaciones': recomendaciones})