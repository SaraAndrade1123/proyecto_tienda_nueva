from django.contrib import admin

from .models import Consumo, DetallePedido, Pedido


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'fecha', 'estado', 'total')
    list_filter = ('estado',)
    inlines = [DetallePedidoInline]


@admin.register(Consumo)
class ConsumoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'producto', 'cantidad', 'valor')