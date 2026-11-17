# Quita los decimales de los precios (pesos colombianos).
# Cambia 3 columnas: producto.precio_unitario, transaccion.precio y transaccion.total.
# Los valores que ya terminan en ,00 se conservan tal cual (3900.00 pasa a 3900).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("productos", "0010_transaccion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="producto",
            name="precio_unitario",
            field=models.DecimalField(decimal_places=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name="transaccion",
            name="precio",
            field=models.DecimalField(decimal_places=0, max_digits=10),
        ),
        migrations.AlterField(
            model_name="transaccion",
            name="total",
            field=models.DecimalField(decimal_places=0, editable=False, max_digits=12),
        ),
    ]