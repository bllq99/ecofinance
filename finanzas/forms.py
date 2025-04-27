from django import forms
from .models import Transaccion, ObjetivoAhorro, Presupuesto

class TransaccionForm(forms.ModelForm):
    class Meta:
        model = Transaccion
        fields = ['descripcion', 'monto', 'tipo']

class ObjetivoForm(forms.ModelForm):
    class Meta:
        model = ObjetivoAhorro
        fields = ['nombre', 'monto_objetivo', 'monto_actual', 'fecha_limite']

class PresupuestoForm(forms.ModelForm):
    class Meta:
        model = Presupuesto
        fields = ['monto']
        labels = {
            'monto': 'Monto del Presupuesto'
        }
        widgets = {
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
        }
