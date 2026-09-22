from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group


@receiver(post_save, sender=User)
def asignar_cliente_por_defecto(sender, instance, created, **kwargs):

    if created:
        cliente, creado = Group.objects.get_or_create(name='Cliente')
        instance.groups.add(cliente)

