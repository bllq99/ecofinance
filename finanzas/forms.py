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
<<<<<<< Updated upstream
=======
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Fondo de emergencia'}),
            'monto_objetivo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'monto_actual': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'fecha_limite': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
        }
        labels = {
            'nombre': 'Nombre del objetivo',
            'monto_objetivo': 'Monto a ahorrar',
            'monto_actual': 'Monto actual',
            'fecha_limite': 'Fecha límite'
        }

    def clean_monto_objetivo(self):
        monto = self.cleaned_data.get('monto_objetivo')
        if monto <= 0:
            raise forms.ValidationError('El monto objetivo debe ser mayor que 0')
        return monto

    def clean_monto_actual(self):
        monto = self.cleaned_data.get('monto_actual')
        if monto < 0:
            raise forms.ValidationError('El monto actual no puede ser negativo')
        return monto

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
>>>>>>> Stashed changes
