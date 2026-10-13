from django.db import models

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

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre_empresa']

    def __str__(self):
        return f"{self.nombre_empresa} ({self.contacto_nombre})"