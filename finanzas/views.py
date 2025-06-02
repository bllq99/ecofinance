from django.shortcuts import render, redirect, get_object_or_404
from .models import Transaccion, ObjetivoAhorro, Presupuesto, SerieRecurrente
from .forms import TransaccionForm, ObjetivoForm, PresupuestoForm
from django.db.models import Sum
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from datetime import datetime, timedelta
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


# 🏠 Dashboard: muestra resumen de ingresos, gastos y objetivos
@login_required
def dashboard(request):
    # Obtener fecha actual
    fecha_actual = timezone.now().date()
    
    # Obtener ingresos totales
    cantidad_transacciones = Transaccion.objects.filter(usuario=request.user).count()

    # Filtrar transacciones para solo incluir las que han ocurrido hasta hoy y pertenecen al usuario
    ingresos = Transaccion.objects.filter(
        usuario=request.user,
        tipo='INGRESO', 
        fecha__lte=fecha_actual
    ).aggregate(Sum('monto'))['monto__sum'] or 0
    
    # Obtener gastos totales
    gastos = Transaccion.objects.filter(
        usuario=request.user,
        tipo='GASTO',
        fecha__lte=fecha_actual
    ).aggregate(Sum('monto'))['monto__sum'] or 0
    
    # Obtener gastos por categoría
    gastos_por_categoria = Transaccion.objects.filter(
        usuario=request.user,
        tipo='GASTO',
        fecha__lte=fecha_actual
    ).values('categoria').annotate(
        total=Sum('monto')
    ).order_by('-total')
    
    # Convertir a lista de diccionarios con categoría y monto
    gastos_categorias = [
        {
            'categoria': item['categoria'] or 'Sin categoría',
            'monto': float(item['total'])
        }
        for item in gastos_por_categoria
    ]
    
    balance = float(ingresos - gastos)
    
    # Obtener objetivos y calcular días restantes
    objetivos = ObjetivoAhorro.objects.filter(usuario=request.user)
    objetivos_por_vencer = []
    objetivos_vencidos = []
    
    # Preparar datos para el gráfico de ahorro
    objetivos_ahorro = []
    total_ahorrado = 0
    
    for objetivo in objetivos:
        # Calcular el progreso
        progreso = (float(objetivo.monto_actual) / float(objetivo.monto_objetivo) * 100) if objetivo.monto_objetivo > 0 else 0
        
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
    
    # Obtener el último presupuesto del usuario
    presupuesto = Presupuesto.objects.filter(usuario=request.user).last()
    presupuesto_monto = float(presupuesto.monto) if presupuesto else 0

    # Obtener las últimas 4 transacciones
    ultimas_transacciones = Transaccion.objects.filter(usuario=request.user).order_by('-fecha', '-id')[:4]

    # Obtener el mes y año actual
    mes_actual = fecha_actual.month
    anio_actual = fecha_actual.year

    # Filtrar gastos del mes actual y agrupar por día
    gastos_dia = (
        Transaccion.objects
        .filter(usuario=request.user, tipo='GASTO', fecha__year=anio_actual, fecha__month=mes_actual)
        .annotate(dia=TruncDay('fecha'))
        .values('dia')
        .annotate(total=Sum('monto'))
        .order_by('dia')
    )

    # Preparar datos para el gráfico
    dias_mes = []
    gastos_por_dia = []

    for gasto in gastos_dia:
        dias_mes.append(gasto['dia'].strftime('%d/%m'))
        gastos_por_dia.append(float(gasto['total']))

    # Agrupar gastos por mes
    gastos_mes = (
        Transaccion.objects
        .filter(usuario=request.user, tipo='GASTO')
        .annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(total=Sum('monto'))
        .order_by('mes')
    )

    # Diccionario para traducir meses al español
    meses_espanol = {
        'Jan': 'Ene', 'Feb': 'Feb', 'Mar': 'Mar', 'Apr': 'Abr', 'May': 'Mayo', 'Jun': 'Jun',
        'Jul': 'Jul', 'Aug': 'Ago', 'Sep': 'Sep', 'Oct': 'Oct', 'Nov': 'Nov', 'Dec': 'Dic'
    }

    meses_gastos = []
    gastos_por_mes = []
    max_gasto = 0
    mes_max_gasto = ""

    for gasto in gastos_mes:
        mes_str = gasto['mes'].strftime('%b %Y')
        # Traducir el mes al español
        mes_abbr, anio = mes_str.split()
        mes_es = meses_espanol.get(mes_abbr, mes_abbr)
        meses_gastos.append(f"{mes_es} {anio}")
        monto = float(gasto['total'])
        gastos_por_mes.append(monto)
        if monto > max_gasto:
            max_gasto = monto
            mes_max_gasto = f"{mes_es} {anio}"

    # Tomar solo los últimos 3 meses
    meses_gastos = meses_gastos[-3:]
    gastos_por_mes = gastos_por_mes[-3:]

    # Recalcular el mes de mayor gasto en este subconjunto
    max_gasto = 0
    mes_max_gasto = ""
    for i, monto in enumerate(gastos_por_mes):
        if monto > max_gasto:
            max_gasto = monto
            mes_max_gasto = meses_gastos[i]

    hoy = timezone.now().date()
    ultimas_transacciones = Transaccion.objects.filter(
        usuario=request.user,
        fecha__lte=hoy  # Solo hasta hoy
    ).order_by('-fecha', '-id')[:10]  # O la cantidad que desees

    return render(request, 'finanzas/dashboard.html', {
        'ingresos': float(ingresos),
        'gastos': float(gastos),
        'balance': balance,
        'objetivos': objetivos,
        'presupuesto': presupuesto_monto,
        'objetivos_por_vencer': objetivos_por_vencer,
        'objetivos_vencidos': objetivos_vencidos,
        'gastos_categorias': json.dumps(gastos_categorias),
        'objetivos_ahorro': json.dumps(objetivos_ahorro),
        'total_ahorrado': float(total_ahorrado),
        'ultimas_transacciones': ultimas_transacciones,
        'gastos_dias_labels': dias_mes,
        'gastos_dias_data': gastos_por_dia,
        'meses_gastos': meses_gastos,
        'gastos_por_mes': gastos_por_mes,
        'mes_max_gasto': mes_max_gasto,
        'max_gasto': max_gasto,
        'fecha_actual': fecha_actual,
    })


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
        transacciones = transacciones.filter(fecha__month=mes)
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
            # Calcular próxima fecha de manera más eficiente
            proxima_fecha = trans_base.fecha_inicio
            dias_desde_inicio = (fecha_actual - trans_base.fecha_inicio).days

            if dias_desde_inicio > 0:
                if trans_base.periodicidad == 'DIARIA':
                    proxima_fecha = trans_base.fecha_inicio + timedelta(days=dias_desde_inicio + 1)
                elif trans_base.periodicidad == 'SEMANAL':
                    semanas = dias_desde_inicio // 7 + 1
                    proxima_fecha = trans_base.fecha_inicio + timedelta(weeks=semanas)
                elif trans_base.periodicidad == 'MENSUAL':
                    # Usar relativedelta para manejo correcto de meses
                    meses_diff = (fecha_actual.year - trans_base.fecha_inicio.year) * 12 + fecha_actual.month - trans_base.fecha_inicio.month
                    if fecha_actual.day < trans_base.fecha_inicio.day:
                         meses_diff -= 1
                    next_month_num = trans_base.fecha_inicio.month + meses_diff + 1
                    next_year = trans_base.fecha_inicio.year + (next_month_num - 1) // 12
                    next_month = (next_month_num - 1) % 12 + 1
                    # Intentar mantener el mismo día, manejar fin de mes
                    try:
                        proxima_fecha = trans_base.fecha_inicio.replace(year=next_year, month=next_month)
                    except ValueError:
                        # Si el día es mayor que los días en el próximo mes, usar el último día del mes
                        proxima_fecha = trans_base.fecha_inicio.replace(year=next_year, month=next_month, day=1) + relativedelta(months=1) - timedelta(days=1)


                elif trans_base.periodicidad == 'ANUAL':
                    # Calcular años pasados y sumar 1
                    años_pasados = fecha_actual.year - trans_base.fecha_inicio.year
                    if fecha_actual < trans_base.fecha_inicio.replace(year=fecha_actual.year):
                        años_pasados -= 1
                    proxima_fecha = trans_base.fecha_inicio + relativedelta(years=años_pasados + 1)


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
                return trans_base.fecha_fin or datetime.date.max # Poner Sin límite al final
            elif campo == 'Periodicidad':
                # Usar el texto legible para ordenar si está disponible
                return item.get('periodicidad_display', trans_base.periodicidad)
            elif campo == 'Próxima Fecha':
                 # Ordenar por None (Sin límite) al final
                return item['proxima_fecha'] if item['proxima_fecha'] is not None else datetime.date.max
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
        tipo = request.POST.get('tipo')
        form = TransaccionForm(request.POST)
        if form.is_valid():
            transaccion = form.save(commit=False)
            transaccion.usuario = request.user
            transaccion.tipo = tipo

            if transaccion.es_recurrente and not transaccion.fecha_inicio:
                transaccion.fecha_inicio = timezone.now()

            transaccion.save()

            # Si es recurrente, crear una SerieRecurrente asociada a esta transacción
            if transaccion.es_recurrente:
                # Asegurarse de que la transacción base tenga fecha_inicio si es recurrente
                if not transaccion.fecha_inicio:
                     transaccion.fecha_inicio = timezone.now().date()
                     transaccion.save() # Guardar la transacción con la fecha de inicio si se añadió

                # Crear la SerieRecurrente y asociarla a la transacción base
                serie = SerieRecurrente.objects.create(
                    usuario=transaccion.usuario,
                    activa=True, # La serie está activa por defecto al crearla
                    ultima_generada=transaccion.fecha_inicio # Inicialmente, la última generada es la primera fecha
                )
                transaccion.serie_recurrente = serie
                transaccion.save() # Guardar la transacción de nuevo para asociar la serie

            messages.success(request, f'Transacción de tipo {tipo} registrada correctamente.')
            # Redirigir a la lista de transacciones después de guardar
            return redirect('lista_transacciones')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.' + str(form.errors))
    else:
        form = TransaccionForm()

    ultimas_transacciones = Transaccion.objects.filter(usuario=request.user).order_by('-fecha', '-id')[:5]

    return render(request, 'finanzas/nueva_transaccion.html', {
        'form': form,
        'ultimas_transacciones': ultimas_transacciones
    })


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
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
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
                categoria="Balance Inicial",
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

            messages.success(request, f'Se han añadido ${monto} al objetivo "{objetivo.nombre}".')
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
        nombre = objetivo.nombre
        objetivo.delete()
        messages.success(request, f'El objetivo "{nombre}" ha sido eliminado correctamente.')
        return redirect('lista_objetivos')
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
        # Obtener los datos del formulario
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password_actual = request.POST.get('password_actual')
        password_nueva = request.POST.get('password_nueva')
        password_confirmar = request.POST.get('password_confirmar')

        # Actualizar nombre
        request.user.first_name = nombre
        request.user.save()

        # Si se proporcionó una nueva contraseña
        if password_nueva:
            if not request.user.check_password(password_actual):
                messages.error(request, 'La contraseña actual es incorrecta')
                return redirect('perfil_usuario')
            
            if password_nueva != password_confirmar:
                messages.error(request, 'Las nuevas contraseñas no coinciden')
                return redirect('perfil_usuario')
            
            request.user.set_password(password_nueva)
            request.user.save()
            messages.success(request, 'Contraseña actualizada correctamente')
            # Reautenticar al usuario después de cambiar la contraseña
            login(request, request.user)
        
        messages.success(request, 'Perfil actualizado correctamente')
        return redirect('perfil_usuario')

    return render(request, 'finanzas/perfil.html', {
        'user': request.user
    })
