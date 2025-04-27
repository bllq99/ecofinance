from django.shortcuts import render, redirect
from .models import Transaccion, ObjetivoAhorro, Presupuesto
from .forms import TransaccionForm, ObjetivoForm, PresupuestoForm
from django.db.models import Sum
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth.models import User


# 🏠 Dashboard: muestra resumen de ingresos, gastos y objetivos
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
    })



# 📄 Lista de transacciones
def lista_transacciones(request):
    transacciones = Transaccion.objects.all().order_by('-fecha')
    return render(request, 'finanzas/lista_transacciones.html', {
        'transacciones': transacciones,
    })


# ➕ Crear nueva transacción
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
