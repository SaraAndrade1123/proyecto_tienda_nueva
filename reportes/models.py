from django.db import models
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone


class Pedido(models.Model):
    """Un pedido/venta. Solo los 'completado' cuentan como ingreso."""

    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    fecha = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=12, choices=ESTADOS, default='pendiente')

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'Pedido #{self.pk} - {self.get_estado_display()}'

    @property
    def total(self):
        linea = ExpressionWrapper(
            F('cantidad') * F('precio_unitario'),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
        return self.detalles.aggregate(t=Sum(linea))['t'] or 0


class DetallePedido(models.Model):
    """Una línea del pedido: producto, cantidad y el precio al que se vendió."""

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey('productos.Producto', on_delete=models.PROTECT, related_name='+')
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        # Si no se indica precio, se toma el actual del producto.
        if self.precio_unitario is None:
            self.precio_unitario = self.producto.precio_unitario
        super().save(*args, **kwargs)

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f'{self.cantidad} x {self.producto}'


class Consumo(models.Model):
    """Consumo personal: producto que se saca del inventario sin venderse."""

    fecha = models.DateTimeField(default=timezone.now)
    producto = models.ForeignKey('productos.Producto', on_delete=models.PROTECT, related_name='+')
    cantidad = models.PositiveIntegerField()
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-fecha']

    def save(self, *args, **kwargs):
        # Si no se indica valor, se calcula con el precio del producto.
        if self.valor is None:
            self.valor = self.producto.precio_unitario * self.cantidad
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Consumo de {self.cantidad} x {self.producto}'