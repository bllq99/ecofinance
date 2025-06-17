import os
import django
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import random

# Configura el entorno de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecofinance.settings')
django.setup()

from django.contrib.auth.models import User
from finanzas.models import Transaccion

def create_dummy_transactions(user_id, num_months=5):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        print(f"Error: El usuario con ID {user_id} no existe.")
        return

    today = datetime.now().date()
    
    tipos_transaccion = ['INGRESO', 'GASTO']
    categorias_ingreso = ['Salario', 'Freelance', 'Inversiones', 'Regalo', 'Ventas']
    categorias_gasto = [
        'Comida', 'Transporte', 'Vivienda', 'Entretenimiento', 'Compras',
        'Salud', 'Educacion', 'Servicios', 'Ropa', 'Otros'
    ]

    print(f"Creando transacciones ficticias para el usuario: {user.username} (ID: {user.id})")

    for i in range(num_months):
        current_month_start = (today - relativedelta(months=i)).replace(day=1)
        current_month_end = (current_month_start + relativedelta(months=1)) - timedelta(days=1)

        print(f"  Generando transacciones para {current_month_start.strftime('%B %Y')}")

        # Generar ingresos (3-5 por mes)
        num_ingresos = random.randint(3, 5)
        for _ in range(num_ingresos):
            monto = random.randint(50000, 500000)
            fecha = current_month_start + timedelta(days=random.randint(0, (current_month_end - current_month_start).days))
            descripcion = f"Ingreso - {random.choice(categorias_ingreso)} - {fecha.strftime('%d/%m')}"
            Transaccion.objects.create(
                usuario=user,
                descripcion=descripcion,
                monto=monto,
                tipo='INGRESO',
                fecha=fecha,
                categoria=random.choice(categorias_ingreso)
            )
            #print(f"    Creado INGRESO: {descripcion} - ${monto}")

        # Generar gastos (5-10 por mes)
        num_gastos = random.randint(5, 10)
        for _ in range(num_gastos):
            monto = random.randint(10000, 200000)
            fecha = current_month_start + timedelta(days=random.randint(0, (current_month_end - current_month_start).days))
            descripcion = f"Gasto - {random.choice(categorias_gasto)} - {fecha.strftime('%d/%m')}"
            Transaccion.objects.create(
                usuario=user,
                descripcion=descripcion,
                monto=monto,
                tipo='GASTO',
                fecha=fecha,
                categoria=random.choice(categorias_gasto)
            )
            #print(f"    Creado GASTO: {descripcion} - ${monto}")
    
    print("\nScript terminado. Transacciones creadas exitosamente.")

if __name__ == "__main__":
    # --- IMPORTANTE: CAMBIA ESTO ---
    # Reemplaza 1 con el ID del usuario al que quieres asignar las transacciones.
    # Puedes encontrar el ID del usuario en la administración de Django (http://127.0.0.1:8000/admin/)
    # o ejecutando en la shell de Django: User.objects.all()
    user_id_to_assign = 1 
    # -------------------------------

    create_dummy_transactions(user_id_to_assign, num_months=5) 