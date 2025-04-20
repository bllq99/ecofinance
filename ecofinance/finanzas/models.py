from django.db import models

class Transaccion(models.Model):
    TIPO_CHOICES = [
        ('INGRESO', 'Ingreso'),
        ('GASTO', 'Gasto'),
    ]

    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    fecha = models.DateField(auto_now_add=True)
    categoria = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.descripcion} - {self.tipo} - ${self.monto}"

class ObjetivoAhorro(models.Model):
    nombre = models.CharField(max_length=255)
    monto_objetivo = models.DecimalField(max_digits=10, decimal_places=2)
    monto_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_limite = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.nombre