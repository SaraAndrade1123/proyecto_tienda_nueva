from django.contrib import admin

from .models import CajaDiaria, Cobro, CobroItem, PagoProveedor


class PagoEnLinea(admin.TabularInline):
    model = PagoProveedor
    extra = 0
    can_delete = False
    fields = ('proveedor_nombre', 'concepto', 'valor', 'registrado_por_nombre', 'creado_en')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(CajaDiaria)
class CajaDiariaAdmin(admin.ModelAdmin):
    """En el admin las cajas solo se MIRAN: se abren y se cierran desde la página de la caja."""
    list_display = ('fecha', 'estado', 'base_inicial', 'ventas_total', 'esperado', 'contado', 'diferencia', 'resultado', 'cerrada_por_nombre')
    list_filter = ('estado', 'resultado')
    date_hierarchy = 'fecha'
    inlines = [PagoEnLinea]

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PagoProveedor)
class PagoProveedorAdmin(admin.ModelAdmin):
    list_display = ('creado_en', 'proveedor_nombre', 'concepto', 'valor', 'caja')
    search_fields = ('proveedor_nombre', 'concepto')

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class CobroItemEnLinea(admin.TabularInline):
    model = CobroItem
    extra = 0
    can_delete = False
    fields = ('transaccion',)
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Cobro)
class CobroAdmin(admin.ModelAdmin):
    """Los cobros del carrito solo se miran: igual que las ventas, no se cambian ni se borran."""
    list_display = ('creado_en', 'metodo', 'total', 'efectivo', 'transferencia', 'vuelto', 'registrado_por_nombre')
    list_filter = ('metodo',)
    date_hierarchy = 'creado_en'
    inlines = [CobroItemEnLinea]

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False