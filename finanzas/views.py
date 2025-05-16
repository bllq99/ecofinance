from django.shortcuts import render, redirect
from .models import Transaccion, ObjetivoAhorro, Presupuesto
from .forms import TransaccionForm, ObjetivoForm, PresupuestoForm
from django.db.models import Sum
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required


# 🏠 Dashboard: muestra resumen de ingresos, gastos y objetivos
@login_required
def dashboard(request):
    ingresos = Transaccion.objects.filter(tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    gastos = Transaccion.objects.filter(tipo='GASTO').aggregate(Sum('monto'))['monto__sum'] or 0
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
        'nombre_usuario': request.user.first_name or request.user.email
    })



# 📄 Lista de transacciones
@login_required
def lista_transacciones(request):
    transacciones = Transaccion.objects.all().order_by('-fecha')
    return render(request, 'finanzas/lista_transacciones.html', {
        'transacciones': transacciones,
    })


# ➕ Crear nueva transacción
@login_required
def nueva_transaccion(request):
    if request.method == 'POST':
        form = TransaccionForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_transacciones')
    else:
        form = TransaccionForm()

    return render(request, 'finanzas/nueva_transaccion.html', {
        'form': form
    })


# 📄 Lista de objetivos de ahorro
@login_required
def lista_objetivos(request):
    objetivos = ObjetivoAhorro.objects.all().order_by('fecha_limite')
    return render(request, 'finanzas/lista_objetivos.html', {
        'objetivos': objetivos,
    })


# ➕ Crear nuevo objetivo de ahorro
@login_required
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
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        try:
            email = request.POST.get('email')
            password = request.POST.get('password')
            
            if not email or not password:
                messages.error(request, 'Por favor, complete todos los campos.')
                return render(request, 'finanzas/login.html')
            try:
                user = User.objects.get(email=email)
                user = authenticate(request, username=user.username, password=password)
            except User.DoesNotExist:
                user = None
            
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido {user.first_name}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Correo o contraseña incorrectos.')
                return render(request, 'finanzas/login.html')
        except Exception as e:
            messages.error(request, 'Error al iniciar sesión. Por favor, intente nuevamente.')
            return render(request, 'finanzas/login.html')
    
    return render(request, 'finanzas/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Has cerrado sesión correctamente.')
    return redirect('login')


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

        if User.objects.filter(email=email).exists():
            return render(request, 'finanzas/registro.html', {
                'error': 'El correo electrónico ya está registrado'
            })

        try:
            user = User.objects.create_user(username=email, email=email, password=password1)
            user.first_name = nombre
            user.save()
            login(request, user)
            messages.success(request, f'¡Bienvenido {nombre}!')
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
