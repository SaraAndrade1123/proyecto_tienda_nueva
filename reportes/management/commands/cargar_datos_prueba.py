import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from productos.models import Producto
from reportes.models import Consumo, DetallePedido, Pedido


class Command(BaseCommand):
    help = 'Crea pedidos y consumos de ejemplo para probar el informe de ingresos.'

    def add_arguments(self, parser):
        parser.add_argument('--limpiar', action='store_true',
                            help='Borra antes todos los pedidos y consumos existentes.')

    def handle(self, *args, **opciones):
        productos = list(Producto.objects.all())
        if not productos:
            raise CommandError('Primero crea algunos productos en el catálogo.')

        if opciones['limpiar']:
            Pedido.objects.all().delete()
            Consumo.objects.all().delete()

        random.seed(10)
        ahora = timezone.now()

        for _ in range(25):
            pedido = Pedido.objects.create(
                fecha=ahora - timedelta(days=random.randint(0, 20), hours=random.randint(0, 23)),
                estado=random.choices(['completado', 'pendiente', 'cancelado'], weights=[7, 2, 1])[0],
            )
            for producto in random.sample(productos, k=min(len(productos), random.randint(1, 4))):
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=producto,
                    cantidad=random.randint(1, 6),
                    precio_unitario=producto.precio_unitario,
                )

        for _ in range(6):
            Consumo.objects.create(
                fecha=ahora - timedelta(days=random.randint(0, 20)),
                producto=random.choice(productos),
                cantidad=random.randint(1, 3),
                descripcion='Consumo de prueba',
            )

        self.stdout.write(self.style.SUCCESS('Datos de prueba creados.'))
