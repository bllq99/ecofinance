from django.db import models
from django.utils import timezone
from dateutil.relativedelta import relativedelta
import datetime
from django.contrib.auth.models import User

class Transaccion(models.Model):
    TIPO_CHOICES = [
        ('INGRESO', 'Ingreso'),
        ('GASTO', 'Gasto'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    fecha = models.DateField(auto_now_add=True)
    categoria = models.CharField(max_length=100, blank=True, null=True)
    es_recurrente = models.BooleanField(default=False)
    periodicidad = models.CharField(max_length=20, blank=True, null=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    serie_recurrente = models.ForeignKey('SerieRecurrente', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.descripcion} - {self.tipo} - ${self.monto}"

class SerieRecurrente(models.Model):
    """
    Modelo para agrupar transacciones que forman parte de la misma serie recurrente.
    Permite identificar y gestionar todas las instancias de una transacción recurrente.
    """
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activa = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Serie recurrente #{self.id}"
    
    def generar_transacciones_programadas(self, transaccion_base, periodo_meses=12):
        """
        Genera transacciones programadas basadas en la periodicidad seleccionada.
        Por defecto, genera transacciones para los próximos 12 meses.
        """
        # Asegurarse de que sea una transacción recurrente
        if not transaccion_base.es_recurrente:
            return
        
        # Determinar la fecha límite (hasta cuándo generar transacciones)
        if transaccion_base.fecha_fin:
            fecha_limite = transaccion_base.fecha_fin
        else:
            # Si no hay fecha de fin, generar para el periodo especificado
            fecha_limite = transaccion_base.fecha_inicio + relativedelta(months=periodo_meses)
    
        # Configurar el incremento según la periodicidad
        incrementos = {
            'diario': relativedelta(days=1),
            'semanal': relativedelta(weeks=1),
            'quincenal': relativedelta(weeks=2),
            'mensual': relativedelta(months=1),
            'semestral': relativedelta(months=6),
            'anual': relativedelta(years=1),
        }
        
        incremento = incrementos.get(transaccion_base.periodicidad)
        if not incremento:
            return
        
        # Empezar desde la fecha de inicio + el primer incremento
        fecha_actual = transaccion_base.fecha_inicio + incremento
        
        # Limitar el número de transacciones diarias para evitar crear demasiadas
        max_transacciones = 90 if transaccion_base.periodicidad == 'diario' else 1000
        contador = 0
        
        # Mantener un registro de las fechas ya procesadas para evitar duplicados
        fechas_procesadas = {transaccion_base.fecha}
        
        # Generar transacciones hasta la fecha límite
        while fecha_actual <= fecha_limite and contador < max_transacciones:
            # Verificar si ya existe una transacción para esta fecha
            if fecha_actual in fechas_procesadas:
                fecha_actual += incremento
                continue
            
            # Registrar la fecha como procesada
            fechas_procesadas.add(fecha_actual)
            
            # Crear nueva transacción con los mismos datos pero fecha diferente
            nueva_transaccion = Transaccion.objects.create(
                usuario=transaccion_base.usuario,
                descripcion=transaccion_base.descripcion,
                monto=transaccion_base.monto,
                tipo=transaccion_base.tipo,
                fecha=fecha_actual,
                categoria=transaccion_base.categoria,
                es_recurrente=True,
                periodicidad=transaccion_base.periodicidad,
                fecha_inicio=transaccion_base.fecha_inicio,
                fecha_fin=transaccion_base.fecha_fin,
                serie_recurrente=self
            )
            
            # Avanzar a la siguiente fecha según la periodicidad
            fecha_actual += incremento
            contador += 1

class ObjetivoAhorro(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    nombre = models.CharField(max_length=255)
    monto_objetivo = models.DecimalField(max_digits=10, decimal_places=2)
    monto_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fecha_limite = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.nombre

class Presupuesto(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_creacion = models.DateTimeField(default=timezone.now)

    class Meta:
        get_latest_by = 'fecha_creacion'

    def __str__(self):
        return f"Presupuesto: ${self.monto}"
