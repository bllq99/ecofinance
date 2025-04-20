from django.shortcuts import render, redirect
from .models import Transaccion, ObjetivoAhorro
from .forms import TransaccionForm, ObjetivoForm
from django.db.models import Sum


# 🏠 Dashboard: muestra resumen de ingresos, gastos y objetivos
def dashboard(request):
    ingresos = Transaccion.objects.filter(tipo='INGRESO').aggregate(Sum('monto'))['monto__sum'] or 0
    gastos = Transaccion.objects.filter(tipo='GASTO').aggregate(Sum('monto'))['monto__sum'] or 0
    balance = ingresos - gastos
    objetivos = ObjetivoAhorro.objects.all()

    return render(request, 'finanzas/dashboard.html', {
        'ingresos': ingresos,
        'gastos': gastos,
        'balance': balance,
        'objetivos': objetivos,
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
