from django.shortcuts import render, redirect
from .models import Transaccion, ObjetivoAhorro
from .forms import TransaccionForm, ObjetivoForm
from django.db.models import Sum
<<<<<<< Updated upstream
=======
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from datetime import datetime
from django.utils import timezone
from itertools import groupby
from django.utils.timezone import localtime
from django.contrib.auth.decorators import login_required
>>>>>>> Stashed changes


# 🏠 Dashboard: muestra resumen de ingresos, gastos y objetivos
@login_required
def dashboard(request):
<<<<<<< Updated upstream
    ingresos = Transaccion.objects.filter(tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    gastos = Transaccion.objects.filter(tipo='GASTO').aggregate(Sum('monto'))['monto__sum'] or 0
    balance = ingresos - gastos
    objetivos = ObjetivoAhorro.objects.all()
=======
    # Obtener fecha actual
    fecha_actual = timezone.now().date()
    
    # Filtrar transacciones para solo incluir las que han ocurrido hasta hoy y pertenecen al usuario
    ingresos = Transaccion.objects.filter(
        usuario=request.user,
        tipo='INGRESO', 
        fecha__lte=fecha_actual
    ).aggregate(Sum('monto'))['monto__sum'] or 0
    
    gastos = Transaccion.objects.filter(
        usuario=request.user,
        tipo='GASTO',
        fecha__lte=fecha_actual
    ).aggregate(Sum('monto'))['monto__sum'] or 0
    
    balance = ingresos - gastos
    
    # Obtener objetivos y calcular días restantes
    objetivos = ObjetivoAhorro.objects.filter(usuario=request.user)
    objetivos_por_vencer = []
    objetivos_vencidos = []
    
    for objetivo in objetivos:
        # Calcular el progreso
        progreso = (objetivo.monto_actual / objetivo.monto_objetivo * 100) if objetivo.monto_objetivo > 0 else 0
        
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
    presupuesto_monto = presupuesto.monto if presupuesto else 0
>>>>>>> Stashed changes

    return render(request, 'finanzas/dashboard.html', {
        'ingresos': ingresos,
        'gastos': gastos,
        'balance': balance,
        'objetivos': objetivos,
<<<<<<< Updated upstream
=======
        'presupuesto': presupuesto_monto,
        'objetivos_por_vencer': objetivos_por_vencer,
        'objetivos_vencidos': objetivos_vencidos
>>>>>>> Stashed changes
    })



# 📄 Lista de transacciones
@login_required
def lista_transacciones(request):
<<<<<<< Updated upstream
    transacciones = Transaccion.objects.all().order_by('-fecha')
=======
    # Verificar si debemos mostrar transacciones futuras
    mostrar_futuras = 'mostrar_futuras' in request.GET
    
    # Obtener fecha actual
    fecha_actual = timezone.now().date()
    
    # Filtrar transacciones según la preferencia
    if mostrar_futuras:
        transacciones = Transaccion.objects.filter(usuario=request.user).order_by('-fecha')
    else:
        transacciones = Transaccion.objects.filter(usuario=request.user, fecha__lte=fecha_actual).order_by('-fecha')
    
    # Crear un diccionario para agrupar transacciones por mes
    transacciones_por_mes = {}
    
    for transaccion in transacciones:
        # Crear clave de año-mes (por ejemplo: "2025-05")
        mes_clave = transaccion.fecha.strftime('%Y-%m')
        
        # Crear entrada para el mes si no existe
        if mes_clave not in transacciones_por_mes:
            # Formatear el nombre del mes para mostrar (por ejemplo: "Mayo 2025")
            nombre_mes = transaccion.fecha.strftime('%B %Y').capitalize()
            transacciones_por_mes[mes_clave] = {
                'nombre': nombre_mes,
                'transacciones': [],
                'total_ingresos': 0,
                'total_gastos': 0
            }
        
        # Agregar la transacción al mes correspondiente
        transacciones_por_mes[mes_clave]['transacciones'].append(transaccion)
        
        # Actualizar totales
        if transaccion.tipo == 'INGRESO':
            transacciones_por_mes[mes_clave]['total_ingresos'] += float(transaccion.monto)
        else:
            transacciones_por_mes[mes_clave]['total_gastos'] += float(transaccion.monto)
    
    # Convertir el diccionario a una lista ordenada por mes (más reciente primero)
    meses = sorted(transacciones_por_mes.items(), key=lambda x: x[0], reverse=True)
    
>>>>>>> Stashed changes
    return render(request, 'finanzas/lista_transacciones.html', {
        'transacciones': transacciones,
    })


# ➕ Crear nueva transacción
@login_required
def nueva_transaccion(request):
    if request.method == 'POST':
<<<<<<< Updated upstream
        form = TransaccionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_transacciones')
    else:
        form = TransaccionForm()

    return render(request, 'finanzas/nueva_transaccion.html', {
        'form': form
    })
=======
        # Obtener datos del formulario
        tipo = request.POST.get('tipo')
        categoria = request.POST.get('categoria')
        descripcion = request.POST.get('descripcion')
        monto = request.POST.get('monto')
        es_recurrente = 'esFijo' in request.POST
        
        # Si es recurrente, usar la fecha de inicio como fecha de la transacción original
        if es_recurrente:
            periodicidad = request.POST.get('periodicidad')
            fecha_inicio_str = request.POST.get('fechaInicio')
            fecha_fin_str = request.POST.get('fechaFin') or None
            
            # Convertir strings a objetos fecha
            fecha_inicio = datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date() if fecha_inicio_str else timezone.now().date()
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d').date() if fecha_fin_str else None
            
            # Crear la transacción con la fecha de inicio como la fecha de la transacción
            nueva_transaccion = Transaccion(
                usuario=request.user,
                tipo=tipo.upper(),
                categoria=categoria,
                descripcion=descripcion,
                monto=monto,
                fecha=fecha_inicio,
                es_recurrente=es_recurrente,
                periodicidad=periodicidad,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            
            # Crear la serie recurrente
            serie = SerieRecurrente.objects.create(usuario=request.user)
            nueva_transaccion.serie_recurrente = serie
            
            # Guardar la transacción base
            nueva_transaccion.save()
            
            # Generar las transacciones programadas
            serie.generar_transacciones_programadas(nueva_transaccion)
            
            messages.success(request, f'Transacción recurrente creada correctamente. Se han programado las repeticiones según la periodicidad seleccionada.')
        else:
            # Para transacciones no recurrentes, usar la fecha actual
            nueva_transaccion = Transaccion(
                usuario=request.user,
                tipo=tipo.upper(),
                categoria=categoria,
                descripcion=descripcion,
                monto=monto,
                fecha=timezone.now(),
                es_recurrente=False
            )
            nueva_transaccion.save()
            messages.success(request, 'Transacción creada correctamente.')
        
        return redirect('lista_transacciones')
        
    return render(request, 'finanzas/nueva_transaccion.html')
>>>>>>> Stashed changes


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
        'objetivos_vencidos': objetivos_vencidos
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
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = ObjetivoForm(initial={'monto_actual': 0})

    return render(request, 'finanzas/nuevo_objetivo.html', {
        'form': form
    })
<<<<<<< Updated upstream
=======


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('dashboard')  # Redirigimos al dashboard
        else:
            return render(request, 'finanzas/login.html', {
                'error': 'Usuario o contraseña incorrectos'
            })
    
    return render(request, 'finanzas/login.html')


def registro_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            return render(request, 'finanzas/registro.html', {
                'error': 'Las contraseñas no coinciden'
            })

        if User.objects.filter(username=username).exists():
            return render(request, 'finanzas/registro.html', {
                'error': 'El nombre de usuario ya existe'
            })

        if User.objects.filter(email=email).exists():
            return render(request, 'finanzas/registro.html', {
                'error': 'El correo electrónico ya está registrado'
            })

        try:
            user = User.objects.create_user(username=username, email=email, password=password1)
            login(request, user)
            return redirect('dashboard')
        except Exception as e:
            return render(request, 'finanzas/registro.html', {
                'error': 'Error al crear el usuario. Por favor, inténtalo de nuevo.'
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
    return redirect('lista_transacciones')  # Cambia 'lista_transacciones' por el nombre de tu vista principal


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
>>>>>>> Stashed changes
