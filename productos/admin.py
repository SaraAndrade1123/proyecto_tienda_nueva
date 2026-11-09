from django.contrib import admin

from .models import Transaccion


def _pesos(valor):
    """3900 -> '$3.900' (pesos colombianos, sin decimales)."""
    return '$' + f'{int(valor):,}'.replace(',', '.')


@admin.register(Transaccion)
class TransaccionAdmin(admin.ModelAdmin):
    """Para CONSULTAR las transacciones en /admin/. Es solo lectura: no se puede agregar, editar ni borrar."""

    list_display = ('id_transaccion', 'fecha_hora', 'nom_producto', 'cantidad', 'precio_pesos', 'total_pesos')
    search_fields = ('nom_producto',)
    date_hierarchy = 'fecha_hora'

    @admin.display(description='Precio', ordering='precio')
    def precio_pesos(self, obj):
        return _pesos(obj.precio)

    @admin.display(description='Total', ordering='total')
    def total_pesos(self, obj):
        return _pesos(obj.total)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False