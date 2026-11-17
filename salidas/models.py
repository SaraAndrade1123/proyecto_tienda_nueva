from django.conf import settings
from django.db import models
from django.utils import timezone

from productos.models import Producto


# Los motivos de la HU_016 y si el proveedor da cambio con cada uno.
MOTIVOS_BASE = [
    ('Producto vencido', True),
    ('Producto dañado o roto', True),
    ('Producto deteriorado o en mal estado', True),
    ('Recibido dañado del proveedor', True),
    ('Recibido con fecha de vencimiento inadecuada', True),
    ('Pérdida o desaparición de mercancía', False),
    ('Otro motivo', False),
]


class MotivoSalida(models.Model):
    """
    Los motivos de baja se manejan como las categorías: se pueden agregar, editar y borrar.
    Cada motivo dice si el proveedor da cambio del producto o no.
    """
    nombre = models.CharField('Motivo', max_length=80, unique=True)
    da_cambio = models.BooleanField('El proveedor da cambio', default=False)

    class Meta:
        verbose_name = 'Motivo de salida'
        verbose_name_plural = 'Motivos de salida'
        ordering = ['id']

    def __str__(self):
        return self.nombre


class SalidaProducto(models.Model):
    """
    HU_016: una salida (baja) de inventario que NO es una venta: vencidos, dañados, pérdidas...
    Cada registro guarda una «foto» del producto y del motivo en ese momento (nombre, precio y
    si había cambio), igual que Transaccion, para que el historial no cambie aunque después
    editen o borren el producto o renombren el motivo.
    """
    producto = models.ForeignKey(
        Producto, on_delete=models.SET_NULL, null=True, blank=True, related_name='salidas',
    )
    nom_producto = models.CharField('Producto', max_length=200)
    precio_unitario = models.DecimalField('Precio unitario', max_digits=10, decimal_places=0)
    cantidad = models.PositiveIntegerField('Cantidad')

    # PROTECT: un motivo que ya se usó no se puede borrar (igual que una categoría con productos).
    motivo = models.ForeignKey(MotivoSalida, on_delete=models.PROTECT, related_name='salidas')
    motivo_nombre = models.CharField('Motivo', max_length=80, editable=False)
    aplica_cambio = models.BooleanField('El proveedor da cambio', default=False, editable=False)

    fecha = models.DateField('Fecha de la baja', default=timezone.localdate, db_index=True)
    descripcion = models.TextField('Descripción de lo sucedido')
    observaciones_recepcion = models.TextField(
        'Condiciones en que llegó', blank=True,
        help_text='Empaque roto, envase abierto, mercancía incompleta...',
    )
    # Opcional. Se guarda donde diga STORAGES['default'] (en la tienda: Cloudinary).
    foto = models.ImageField('Fotografía de evidencia', upload_to='salidas/', null=True, blank=True)

    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='salidas_registradas',
    )
    registrado_por_nombre = models.CharField('Registrado por', max_length=150, blank=True)
    creado_en = models.DateTimeField('Registrado el', default=timezone.now, editable=False)

    class Meta:
        verbose_name = 'Salida de producto'
        verbose_name_plural = 'Salidas de productos'
        ordering = ['-fecha', '-creado_en', '-id']

    def save(self, *args, **kwargs):
        # Al crearla se copia el motivo tal como está hoy: nadie marca el cambio a mano.
        if self._state.adding and self.motivo_id:
            self.motivo_nombre = self.motivo.nombre
            self.aplica_cambio = self.motivo.da_cambio
        super().save(*args, **kwargs)

    @property
    def motivo_texto(self):
        return self.motivo_nombre

    @property
    def valor_perdido(self):
        return self.precio_unitario * self.cantidad

    def __str__(self):
        return f'Salida #{self.pk} · {self.cantidad} de {self.nom_producto} ({self.motivo_nombre})'