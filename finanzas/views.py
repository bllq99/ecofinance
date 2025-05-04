from django.shortcuts import render, redirect, get_object_or_404
from .models import Transaccion, ObjetivoAhorro, Presupuesto, SerieRecurrente
from .forms import TransaccionForm, ObjetivoForm, PresupuestoForm
from django.db.models import Sum
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User
from datetime import datetime
from django.utils import timezone
from itertools import groupby
from django.utils.timezone import localtime


# 🏠 Dashboard: muestra resumen de ingresos, gastos y objetivos
def dashboard(request):
    # Obtener fecha actual
    fecha_actual = timezone.now().date()
    
    # Filtrar transacciones para solo incluir las que han ocurrido hasta hoy
    ingresos = Transaccion.objects.filter(
        tipo='INGRESO', 
        fecha__lte=fecha_actual  # Solo fechas menores o iguales a la actual
    ).aggregate(Sum('monto'))['monto__sum'] or 0
    
    gastos = Transaccion.objects.filter(
        tipo='GASTO',
        fecha__lte=fecha_actual  # Solo fechas menores o iguales a la actual
    ).aggregate(Sum('monto'))['monto__sum'] or 0
    
    balance = ingresos - gastos
    objetivos = ObjetivoAhorro.objects.all()
    
    # Obtener el último presupuesto
    presupuesto = Presupuesto.objects.last()
    presupuesto_monto = presupuesto.monto if presupuesto else 0

    return render(request, 'finanzas/dashboard.html', {
        'ingresos': ingresos,
        'gastos': gastos,
        'balance': balance,
        'objetivos': objetivos,
        'presupuesto': presupuesto_monto,
    })



# 📄 Lista de transacciones
def lista_transacciones(request):
    # Verificar si debemos mostrar transacciones futuras
    mostrar_futuras = 'mostrar_futuras' in request.GET
    
    # Obtener fecha actual
    fecha_actual = timezone.now().date()
    
    # Filtrar transacciones según la preferencia
    if mostrar_futuras:
        transacciones = Transaccion.objects.all().order_by('-fecha')
    else:
        transacciones = Transaccion.objects.filter(fecha__lte=fecha_actual).order_by('-fecha')
    
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
    
    return render(request, 'finanzas/lista_transacciones.html', {
        'meses': meses,
    })


# ➕ Crear nueva transacción
def nueva_transaccion(request):
    if request.method == 'POST':
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
                tipo=tipo.upper(),
                categoria=categoria,
                descripcion=descripcion,
                monto=monto,
                fecha=fecha_inicio,  # Usar la fecha de inicio en lugar de now()
                es_recurrente=es_recurrente,
                periodicidad=periodicidad,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )
            
            # Crear la serie recurrente
            serie = SerieRecurrente.objects.create()
            nueva_transaccion.serie_recurrente = serie
            
            # Guardar la transacción base
            nueva_transaccion.save()
            
            # Generar las transacciones programadas
            serie.generar_transacciones_programadas(nueva_transaccion)
            
            messages.success(request, f'Transacción recurrente creada correctamente. Se han programado las repeticiones según la periodicidad seleccionada.')
        else:
            # Para transacciones no recurrentes, usar la fecha actual
            nueva_transaccion = Transaccion(
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


# 📄 Lista de objetivos de ahorro
def lista_objetivos(request):
    objetivos = ObjetivoAhorro.objects.all().order_by('fecha_limite')
    return render(request, 'finanzas/lista_objetivos.html', {
        'objetivos': objetivos,
    })


# ➕ Crear nuevo objetivo de ahorro
def nuevo_objetivo(request):
    if request.method == 'POST':
        form = ObjetivoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_objetivos')
    else:
        form = ObjetivoForm()

    return render(request, 'finanzas/nuevo_objetivo.html', {
        'form': form
    })


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


def establecer_presupuesto(request):
    if request.method == 'POST':
        form = PresupuestoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Presupuesto establecido correctamente')
            return redirect('dashboard')
    else:
        form = PresupuestoForm()

    return render(request, 'finanzas/establecer_presupuesto.html', {
        'form': form
    })


def eliminar_transaccion(request, id):
    transaccion = get_object_or_404(Transaccion, id=id)
    transaccion.delete()
    messages.success(request, "Transacción eliminada con éxito.")
    return redirect('lista_transacciones')  # Cambia 'lista_transacciones' por el nombre de tu vista principal
