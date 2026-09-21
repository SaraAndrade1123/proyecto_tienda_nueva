from django.db import models

# Create your models here.

class Producto(models.Model):
    
    nombre = models.CharField(max_length=100)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.IntegerField()
    unidad_medida = models.CharField(max_length=50)
    categoria = models.CharField(max_length=100)
    existencias = models.IntegerField()
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)

    def __str__(self):
        return self.nombre