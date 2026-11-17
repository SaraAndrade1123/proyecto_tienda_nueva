from django.contrib import admin

from .models import MotivoSalida, SalidaProducto


@admin.register(MotivoSalida)
class MotivoSalidaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'da_cambio')
    list_editable = ('da_cambio',)
    search_fields = ('nombre',)


@admin.register(SalidaProducto)
class SalidaProductoAdmin(admin.ModelAdmin):
    """Solo lectura: las salidas se registran desde la app (así se descuenta el inventario)."""
    list_display = ('id', 'fecha', 'nom_producto', 'cantidad', 'motivo_nombre', 'aplica_cambio', 'registrado_por_nombre')
    list_filter = ('motivo', 'aplica_cambio', 'fecha')
    search_fields = ('nom_producto', 'descripcion', 'motivo_nombre')
    date_hierarchy = 'fecha'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False