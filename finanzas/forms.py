from django import forms
from .models import Transaccion, ObjetivoAhorro

class TransaccionForm(forms.ModelForm):
    class Meta:
        model = Transaccion
        fields = ['descripcion', 'monto', 'tipo']

class ObjetivoForm(forms.ModelForm):
    class Meta:
        model = ObjetivoAhorro
        fields = ['nombre', 'monto_objetivo', 'monto_actual', 'fecha_limite']
