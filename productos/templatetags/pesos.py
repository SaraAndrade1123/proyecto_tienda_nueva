from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def pesos(valor):
    """Pesos colombianos sin decimales y con punto de miles:  3900 -> '3.900'.

    Uso en una plantilla:   ${{ producto.precio_unitario|pesos }}   ->   $3.900
    (No depende del idioma ni de la configuración regional del servidor.)"""
    try:
        numero = int(Decimal(str(valor)).quantize(Decimal(1)))
    except (InvalidOperation, ValueError, TypeError):
        return valor
    return f'{numero:,}'.replace(',', '.')