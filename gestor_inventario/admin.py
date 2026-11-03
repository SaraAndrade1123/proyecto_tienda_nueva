from django.contrib import admin

from .models import (
    Proveedor,
    VisitaProveedor,
    Perfil,
    ImagenCarrusel,
    Persona,
    ConsumoPersonal,
    DetalleConsumo,
)

class VisitaProveedorInline(admin.TabularInline):
    model = VisitaProveedor
    extra = 1


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre_empresa', 'nit', 'contacto_nombre', 'telefono', 'email', 'activo')
    search_fields = ('nombre_empresa', 'nit', 'email')
    list_filter = ('activo',)
    inlines = [VisitaProveedorInline]


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user',)


@admin.register(ImagenCarrusel)
class ImagenCarruselAdmin(admin.ModelAdmin):
    list_display = ('id', 'orden', 'fecha_creacion')
    ordering = ('orden',)


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'activo', 'creado_en')
    list_filter = ('activo',)
    search_fields = ('nombre',)


class DetalleConsumoInline(admin.TabularInline):
    model = DetalleConsumo
    extra = 0
    readonly_fields = ('subtotal',)


@admin.register(ConsumoPersonal)
class ConsumoPersonalAdmin(admin.ModelAdmin):
    list_display = ('id', 'persona', 'fecha', 'total', 'activo')
    list_filter = ('activo', 'fecha', 'persona')
    search_fields = ('persona__nombre',)
    inlines = [DetalleConsumoInline]