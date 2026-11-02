from django.db import models
from django.utils import timezone
from django.conf import settings

from cloudinary.models import CloudinaryField


class Proveedor(models.Model):
    nombre_empresa = models.CharField(max_length=200, verbose_name="Nombre de la empresa / Razón Social", default='')
    nit = models.CharField(max_length=20, unique=True, verbose_name="NIT")
    contacto_nombre = models.CharField(max_length=150, verbose_name="Nombre del contacto", default='')
    telefono = models.CharField(max_length=20, verbose_name="Teléfono", default='')
    email = models.EmailField(verbose_name="Correo electrónico", default='')
    direccion = models.CharField(max_length=250, blank=True, null=True, verbose_name="Dirección")
    activo = models.BooleanField(default=True, verbose_name="Proveedor Activo")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    proxima_visita = models.DateField(null=True, blank=True, verbose_name="Próxima visita")

    def __str__(self):
        return self.nombre_empresa

class VisitaProveedor(models.Model):
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name='visitas',
    )
    fecha = models.DateField()

    class Meta:
        ordering = ['fecha']

    def __str__(self):
        return f"{self.proveedor.nombre_empresa} - {self.fecha}"

class Perfil(models.Model):
    '''
    Datos adicionales del usuario (foto de perfil).
    '''
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    foto = models.ImageField(upload_to='perfiles/', blank=True, null=True)

    def __str__(self):
        return f"Perfil de {self.user}"

class ImagenCarrusel(models.Model):
    imagen = models.ImageField(upload_to='carrusel/')
    orden = models.PositiveIntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden']

    def save(self, *args, **kwargs):
        if not self.pk and not self.orden:
            ultimo = ImagenCarrusel.objects.order_by('-orden').first()
            self.orden = (ultimo.orden + 1) if ultimo else 1
        super().save(*args, **kwargs)