from django.db import migrations, models
import django.db.models.deletion


def convertir_categorias(apps, schema_editor):
    """
    Convierte las categorías antiguas almacenadas como texto
    a las categorías almacenadas en la tabla Categoria.
    """

    Producto = apps.get_model('productos', 'Producto')
    Categoria = apps.get_model('productos', 'Categoria')

    # Usamos get_or_create para que no falle si la categoría no existe
    nombres_categorias = [
        'Lacteos', 'Bebidas', 'Verduras', 'Frutas', 'Enlatados',
        'Dulces', 'Embutidos', 'Granos', 'Legumbres', 'Paqueteria'
    ]

    relaciones = {}
    for nombre in nombres_categorias:
        categoria, _ = Categoria.objects.get_or_create(nombre=nombre)
        relaciones[nombre] = categoria.id

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