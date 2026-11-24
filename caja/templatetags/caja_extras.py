from django import template

register = template.Library()


@register.filter
def plata(valor):
    """Como |pesos pero con el signo y el $ incluidos:  -5000 -> '-$5.000',  5000 -> '$5.000'."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return valor
    texto = f'{abs(numero):,}'.replace(',', '.')
    return f'-${texto}' if numero < 0 else f'${texto}'