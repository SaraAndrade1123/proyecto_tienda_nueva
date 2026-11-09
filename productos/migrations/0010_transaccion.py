# Variante B: úsala si en tu carpeta NO existe 0010_venta.py.
# Crea la tabla Transaccion desde cero.

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("productos", "0009_alter_producto_categoria"),
    ]

    operations = [
        migrations.CreateModel(
            name="Transaccion",
            fields=[
                ("id_transaccion", models.BigAutoField(primary_key=True, serialize=False)),
                ("nom_producto", models.CharField(max_length=200)),
                (
                    "fecha_hora",
                    models.DateTimeField(
                        db_index=True, default=django.utils.timezone.now, editable=False
                    ),
                ),
                ("cantidad", models.PositiveIntegerField()),
                ("precio", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "total",
                    models.DecimalField(
                        decimal_places=2, editable=False, max_digits=12
                    ),
                ),
            ],
            options={
                "verbose_name": "Transacción",
                "verbose_name_plural": "Transacciones",
                "ordering": ["-fecha_hora", "-id_transaccion"],
            },
        ),
    ]