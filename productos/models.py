
from decimal import Decimal
 
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

class Categoria(models.Model):

    nombre = models.CharField(
        max_length=100,
        unique=True
    )

    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):

    UNIDADES_CHOICES = [
        ('Kg', 'Kilogramos (kg)'),
        ('Litros', 'Litros (L)'),
        ('Gramos', 'Gramos (g)'),
        ('Mililitros', 'Mililitros (ml)')
    ]

    nombre = models.CharField(
        max_length=200
    )

    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=0
    )

    cantidad = models.IntegerField()

    existencias = models.IntegerField()

    imagen = models.ImageField(
        upload_to='productos/',
        null=True,
        blank=True
    )

    descripcion = models.TextField(
        blank=True
    )

    unidad_medida = models.CharField(
        max_length=20,
        choices=UNIDADES_CHOICES,
        default=''
    )

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='productos',
        null=True,
        blank=True
    )
    
    class Meta:
        # Siempre en orden alfabético (sin importar mayúsculas): lista, catálogo y admin
        ordering = [Lower('nombre')]

    def __str__(self):
        return self.nombre


class TransaccionQuerySet(models.QuerySet):

 
    def update(self, **campos):
        raise ValidationError('Las transacciones registradas no se pueden modificar.')
 
    def delete(self):
        raise ValidationError('Las transacciones registradas no se pueden borrar.')
 
 
class Transaccion(models.Model):
   
 
    # Número único de la transacción. Lo asigna la base de datos sola: 1, 2, 3...
    id_transaccion = models.BigAutoField(primary_key=True)
 
    # Nombre del producto TAL COMO ESTABA al vender (es texto copiado, no un enlace).
    nom_producto = models.CharField(max_length=200)
 
    # Fecha y hora exactas (con segundos) en que se registró. Se llena sola; no se escribe a mano.
    fecha_hora = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
 
    # Cuántas unidades se vendieron (entero de 0 en adelante; la vista exige 1 o más).
    cantidad = models.PositiveIntegerField()
 
    # Precio de UNA unidad en el momento de la venta.
    precio = models.DecimalField(max_digits=10, decimal_places=0)
 
    # precio × cantidad. Lo calcula save(); nadie lo escribe a mano.
    total = models.DecimalField(max_digits=12, decimal_places=0, editable=False)
 
    objects = TransaccionQuerySet.as_manager()
 
    class Meta:
        verbose_name = 'Transacción'
        verbose_name_plural = 'Transacciones'
        # La más reciente primero (y si dos caen en el mismo instante, la de número mayor).
        ordering = ['-fecha_hora', '-id_transaccion']
 
    def save(self, *args, **kwargs):
        # Solo se permite CREAR. Si la fila ya existe en la base de datos, no se toca.
        if not self._state.adding:
            raise ValidationError('Las transacciones registradas no se pueden modificar.')
 
        # El total lo calcula el modelo (precio guardado × cantidad). Decimal(str(...)) evita
        # errores de redondeo y funciona aunque alguien pase el precio como texto o como float.
        self.total = Decimal(str(self.precio)) * int(self.cantidad)
        super().save(*args, **kwargs)
 
    def delete(self, *args, **kwargs):
        raise ValidationError('Las transacciones registradas no se pueden borrar.')
 
    def __str__(self):
        return f'#{self.id_transaccion} · {self.cantidad} x {self.nom_producto} ({self.fecha_hora:%d/%m/%Y %H:%M:%S})'