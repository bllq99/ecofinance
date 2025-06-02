from django import forms
from .models import Transaccion, ObjetivoAhorro, Presupuesto
from django.utils.timezone import now

class TransaccionForm(forms.ModelForm):
    es_recurrente = forms.BooleanField(
        required=False,
        label='¿Es una transacción recurrente?',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    periodicidad = forms.ChoiceField(
        required=False,
        choices=[
            ('DIARIA', 'Diaria'),
            ('SEMANAL', 'Semanal'),
            ('MENSUAL', 'Mensual'),
            ('ANUAL', 'Anual')
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    fecha_inicio = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    fecha_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )

    class Meta:
        model = Transaccion
        fields = ['monto', 'descripcion', 'categoria', 'es_recurrente', 'periodicidad', 'fecha_fin']
        widgets = {
            'tipo': forms.Select(
                choices=[('INGRESO', 'Ingreso'), ('GASTO', 'Gasto')],
                attrs={'class': 'form-control'}
            ),
            'categoria': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'})
        }
        labels = {
            'tipo': 'Tipo de transacción',
            'categoria': 'Categoría',
            'descripcion': 'Descripción',
            'monto': 'Monto'
        }

    def clean(self):
        cleaned_data = super().clean()
        es_recurrente = cleaned_data.get('es_recurrente')
        periodicidad = cleaned_data.get('periodicidad')
        fecha_inicio = cleaned_data.get('fecha_inicio')
        fecha_fin = cleaned_data.get('fecha_fin')

        if es_recurrente:
            if not periodicidad:
                raise forms.ValidationError('Debes seleccionar una periodicidad para transacciones recurrentes')
            if fecha_fin and fecha_inicio and fecha_fin < fecha_inicio:
                raise forms.ValidationError('La fecha de fin debe ser posterior a la fecha de inicio')

        return cleaned_data

class ObjetivoForm(forms.ModelForm):
    class Meta:
        model = ObjetivoAhorro
        fields = ['nombre', 'monto_objetivo', 'monto_actual', 'fecha_limite']
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Configurar el atributo 'min' para el campo fecha_limite
        self.fields['fecha_limite'].widget.attrs['min'] = now().date().isoformat()

    def clean_monto_objetivo(self):
        monto = self.cleaned_data.get('monto_objetivo')
        if monto <= 0:
            raise forms.ValidationError('El monto objetivo debe ser mayor que 0')
        return monto

    def clean_monto_actual(self):
        monto = self.cleaned_data.get('monto_actual')
        if monto < 0:
            raise forms.ValidationError('El monto actual no puede ser negativo')
        monto_actual = self.cleaned_data.get('monto_actual')
        monto_objetivo = self.cleaned_data.get('monto_objetivo')
        if monto_actual and monto_objetivo and monto_actual > monto_objetivo:
            raise forms.ValidationError("El monto actual no puede exceder el monto objetivo.")
        return monto
    
    def clean_fecha_limite(self):
        fecha_limite = self.cleaned_data.get('fecha_limite')
        if fecha_limite and fecha_limite <= now().date():
            raise forms.ValidationError("La fecha límite debe ser una fecha futura.")
        return fecha_limite

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
