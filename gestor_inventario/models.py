from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)


class Proveedor(models.Model):
    nombre_empresa = models.CharField(max_length=200, verbose_name="Nombre de la empresa / Razón Social")
    nit = models.CharField(max_length=20, unique=True, verbose_name="NIT")
    contacto_nombre = models.CharField(max_length=150, verbose_name="Nombre del contacto")
    telefono = models.CharField(max_length=20, verbose_name="Teléfono")
    email = models.EmailField(verbose_name="Correo electrónico")
    direccion = models.CharField(max_length=250, blank=True, null=True, verbose_name="Dirección")
    activo = models.BooleanField(default=True, verbose_name="Proveedor Activo")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    proxima_visita = models.DateField(null=True, blank=True, verbose_name="Próxima visita")

    def __str__(self):
        return self.nombre_empresa


# ============================================================
# NUEVO MODELO PARA EL CARRUSEL DE IMÁGENES
# ============================================================
class ImagenCarrusel(models.Model):
    imagen = models.ImageField(upload_to='carrusel/', verbose_name="Imagen")
    orden = models.PositiveIntegerField(default=0, verbose_name="Orden de visualización")
    fecha_creacion = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")

    class Meta:
        ordering = ['orden', 'fecha_creacion']
        verbose_name = 'Imagen del Carrusel'
        verbose_name_plural = 'Imágenes del Carrusel'

    def __str__(self):
        return f"Imagen #{self.id} - Orden {self.orden}"