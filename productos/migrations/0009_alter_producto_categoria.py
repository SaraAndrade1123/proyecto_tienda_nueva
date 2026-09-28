from django.db import migrations, models
import django.db.models.deletion


def convertir_categorias(apps, schema_editor):
    """
    Convierte las categorías antiguas almacenadas como texto
    a las categorías almacenadas en la tabla Categoria.
    """

    Producto = apps.get_model('productos', 'Producto')
    Categoria = apps.get_model('productos', 'Categoria')

    relaciones = {
        'Lacteos': Categoria.objects.get(nombre='Lacteos').id,
        'Bebidas': Categoria.objects.get(nombre='Bebidas').id,
        'Verduras': Categoria.objects.get(nombre='Verduras').id,
        'Frutas': Categoria.objects.get(nombre='Frutas').id,
        'Enlatados': Categoria.objects.get(nombre='Enlatados').id,
        'Dulces': Categoria.objects.get(nombre='Dulces').id,
        'Embutidos': Categoria.objects.get(nombre='Embutidos').id,
        'Granos': Categoria.objects.get(nombre='Granos').id,
        'Legumbres': Categoria.objects.get(nombre='Legumbres').id,
        'Paqueteria': Categoria.objects.get(nombre='Paqueteria').id,
    }

    for producto in Producto.objects.all():

        categoria_antigua = producto.categoria

        if categoria_antigua in relaciones:
            producto.categoria = relaciones[categoria_antigua]
            producto.save(update_fields=['categoria'])


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0008_categoria_alter_producto_categoria'),
    ]

    operations = [

        migrations.AlterField(
            model_name='producto',
            name='categoria',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='productos',
                to='productos.categoria',
            ),
        ),

        migrations.RunPython(
            convertir_categorias,
            migrations.RunPython.noop,
        ),
    ]