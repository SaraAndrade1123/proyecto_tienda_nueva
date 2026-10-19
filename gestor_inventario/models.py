from django.db import models
from django.utils import timezone
from django.conf import settings

class Proyecto(models.Model):
    '''
    Modelo que representa un proyecto
    '''
    nombre = models.CharField(max_length=100) #Campo de texto (varchar)
    descripcion = models.TextField() #texto largo
    duracion = models.IntegerField() #entero
    imagen = models.ImageField(upload_to = 'img/', default = 'img/logo.png')
    def __str__(self):
        return self.nombre

class Tarea(models.Model):
    '''
    modelo que representa la tarea de un proyecto
    '''

    PRIORIDAD_CHOICES = [
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
    ]
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('EN_PROGRESO', 'En progreso'),
        ('COMPLETADA', 'Completada'),
    ]
    
    # relacion 1 a muchos: un proyecto tiene muchas tareas
    proyecto = models.ForeignKey(
        Proyecto,
        on_delete = models.CASCADE,
        related_name='tareas',
    )
    titulo = models.CharField(max_length=50)
    prioridad = models.CharField(
        max_length=5,
        choices= PRIORIDAD_CHOICES,
        default='MEDIA')
    estado = models.CharField(
        max_length=11,
        choices= ESTADO_CHOICES,
        default='PENDIENTE'
    )
    def __str__(self):
        return self.titulo + "(" + self.proyecto.nombre + ")"


class Proveedor(models.Model):
    '''
    Modelo que representa un proveedor que surte productos.
    HU_008: CRUD_PROVEEDOR
    '''
    nombre = models.CharField(max_length=150)
    # unique=True hace que la BD rechace un NIT repetido (criterio: "si el NIT ya existe no se guarda")
    nit = models.CharField(max_length=20, unique=True)
    telefono_contacto = models.CharField(max_length=20)
    correo = models.EmailField()
    # desactivar en vez de borrar: no aparece en activos pero conserva su historial
    activo = models.BooleanField(default=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.nit})"

    def proxima_visita(self):
        '''
        Devuelve la próxima visita (fecha más cercana, hoy o en el futuro) o None si no hay.
        '''
        hoy = timezone.now().date()
        return self.visitas.filter(fecha__gte=hoy).order_by('fecha').first()


class VisitaProveedor(models.Model):
    '''
    Fecha de visita programada de un proveedor.
    Un proveedor puede tener varias fechas de visita (historial + próximas).
    '''
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.CASCADE,
        related_name='visitas',
    )
    fecha = models.DateField()

    class Meta:
        ordering = ['fecha']

    def __str__(self):
        return f"{self.proveedor.nombre} - {self.fecha}"


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