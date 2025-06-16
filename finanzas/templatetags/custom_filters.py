from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def subtract(value, arg):
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0 
    
@register.filter
def formato_clp(value):
    """
    Formatea un número como Pesos Chilenos (CLP).
    Ejemplo: 1234567 -> $1.234.567
    """
    try:
        value = int(value)  # Convertir a entero
        return f"${value:,}".replace(",", ".")  # Agregar separadores de miles con puntos
    except (ValueError, TypeError):
        return value  # Si no es un número, devolver el valor original

@register.filter
def icono_categoria(categoria):
    iconos = {
        'Alimentos': 'fas fa-utensils',
        'Transporte': 'fas fa-bus',
        'Entretenimiento': 'fas fa-film',
        'Salud': 'fas fa-heartbeat',
        'Educación': 'fas fa-book',
        'Ahorro': 'fas fa-piggy-bank',
        'Vivienda': 'fas fa-home',
        'Sueldo': 'fas fa-money-bill-wave',
    }
    return iconos.get(categoria, 'fas fa-receipt') 