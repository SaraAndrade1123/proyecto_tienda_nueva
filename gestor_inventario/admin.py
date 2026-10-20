from django.contrib import admin
from .models import Proveedor, VisitaProveedor


class VisitaProveedorInline(admin.TabularInline):
    model = VisitaProveedor
    extra = 1
#

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = (
        'nombre_empresa',
        'nit',
        'contacto_nombre',
        'telefono',
        'email',
        'activo',
        'fecha_registro',
    )

    list_filter = ('activo',)

    search_fields = (
        'nombre_empresa',
        'nit',
        'contacto_nombre',
    )

    inlines = [VisitaProveedorInline]


admin.site.register(Producto)
admin.site.register(Perfil)
admin.site.register(ImagenCarrusel)