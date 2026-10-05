from django.db import models


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
        decimal_places=2
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

    def __str__(self):
        return self.nombre