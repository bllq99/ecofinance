from django.shortcuts import render, redirect, get_object_or_404
from .models import Transaccion, ObjetivoAhorro, Presupuesto, SerieRecurrente
from .forms import TransaccionForm, ObjetivoForm, PresupuestoForm
from django.db.models import Sum
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from datetime import datetime
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
    mostrar_futuras = 'mostrar_futuras' in request.GET
    fecha_actual = timezone.now().date()
    desde = fecha_actual.replace(day=1)
    hasta = fecha_actual.replace(day=28) + relativedelta(days=4)
    hasta = hasta - relativedelta(days=hasta.day-1)  # último día del mes

    # Genera las transacciones recurrentes necesarias para el rango consultado
    generar_transacciones_recurrentes(request.user, desde, hasta)

    orden = request.GET.get('orden')

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
        ordenes = ['descripcion', 'fecha', 'id']
    elif orden == '-descripcion':
        ordenes = ['-descripcion', '-fecha', '-id']
    else:
        ordenes = [orden, '-fecha', '-id']

    if mostrar_futuras:
        transacciones = Transaccion.objects.filter(usuario=request.user).order_by(*ordenes)
    else:
        transacciones = Transaccion.objects.filter(usuario=request.user, fecha__lte=fecha_actual).order_by(*ordenes)

    # Diccionario para traducir meses al español
    meses_espanol = {
        'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
        'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
        'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
    }

    nombre_mes = None
    if transacciones.exists():
        mes_actual = transacciones.first().fecha.strftime('%B %Y')
        nombre_mes = meses_espanol[mes_actual.split()[0]] + ' ' + mes_actual.split()[1]

    page = request.GET.get('page', 1)
    paginator = Paginator(transacciones, 10)
    try:
        transacciones_paginadas = paginator.page(page)
    except PageNotAnInteger:
        transacciones_paginadas = paginator.page(1)
    except EmptyPage:
        transacciones_paginadas = paginator.page(paginator.num_pages)

    series_recurrentes = SerieRecurrente.objects.filter(usuario=request.user, activa=True)
    today = timezone.now().date()

    series_con_base = []
    for serie in series_recurrentes:
        trans_base = serie.transaccion_set.order_by('fecha').first()
        # Buscar la próxima transacción futura
        proxima = serie.transaccion_set.filter(fecha__gt=today).order_by('fecha').first()
        series_con_base.append({
            'serie': serie,
            'trans': trans_base,
            'proxima': proxima.fecha if proxima else None
        })

    return render(request, 'finanzas/lista_transacciones.html', {
        'transacciones': transacciones_paginadas,
        'orden_actual': orden,
        'nombre_mes': nombre_mes,
        'series_con_base': series_con_base,
        'today': today,
    })


# ➕ Crear nueva transacción
@login_required
def nueva_transaccion(request):
    if request.method == 'POST':
        tipo = request.POST.get('tipo')  # Capturar el tipo de transacción (INGRESO o GASTO)
        form = TransaccionForm(request.POST)
        if form.is_valid():
            transaccion = form.save(commit=False)
            transaccion.usuario = request.user
            transaccion.tipo = tipo  # Asignar el tipo de transacción

            # Si es recurrente, asignar la fecha de inicio como la actual
            if transaccion.es_recurrente and not transaccion.fecha_inicio:
                transaccion.fecha_inicio = timezone.now()

            transaccion.save()
            messages.success(request, f'Transacción de tipo {tipo} registrada correctamente.')
            return redirect('nueva_transaccion')
        else:
            # Mostrar errores del formulario
            messages.error(request, 'Por favor, corrige los errores en el formulario.' + str(form.errors))
    else:
        form = TransaccionForm()

    # Obtener las últimas 5 transacciones del usuario
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
            messages.success(request, '¡Bienvenido! Has iniciado sesión correctamente.')
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

        if User.objects.filter(username=email).exists():
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
