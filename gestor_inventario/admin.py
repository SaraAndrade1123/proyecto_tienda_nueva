from django.contrib import admin
from .models import Proveedor, VisitaProveedor


class VisitaProveedorInline(admin.TabularInline):
    model = VisitaProveedor
    extra = 1


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'nit', 'telefono_contacto', 'correo', 'activo', 'fecha_registro')
    list_filter = ('activo',)
    search_fields = ('nombre', 'nit')
    inlines = [VisitaProveedorInline]


admin.site.register(Proyecto)
admin.site.register(Tarea)
