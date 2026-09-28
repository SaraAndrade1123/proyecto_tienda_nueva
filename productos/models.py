from django.db import models

class Producto(models.Model):
    
    UNIDADES_CHOICES = [
        
        ('Kg', 'Kilogramos (kg)'),
        ('Litros', 'Litros (L)'),
        ('Gramos', 'Gramos (g)'),
        
    ]

    CATEGORIAS_CHOICES = [
        ('Lacteos', 'Lacteos'),
        ('Bebidas', 'Bebidas'),
        ('Verduras', 'Verduras'),
        ('Frutas', 'Frutas'),
        ('Enlatados', 'Enlatados'),
        ('Dulces','Dulces'),
        ('Embutidos','Embutidos'),
        ('Granos','Granos'),
        ('Legumbres','Legumbres'),
        ('',''),
    ]

    nombre = models.CharField(max_length=200)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad = models.IntegerField()
    existencias = models.IntegerField()
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)

  
    unidad_medida = models.CharField(
        max_length=20,
        choices=UNIDADES_CHOICES,
        default='Kg'
    )
    
    categoria = models.CharField(
        max_length=50,
        choices=CATEGORIAS_CHOICES,
        default='Lacteos'
    )

    def __str__(self):
        return self.nombre