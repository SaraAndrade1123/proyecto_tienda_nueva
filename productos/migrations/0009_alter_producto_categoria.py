from django.db import migrations, models
import django.db.models.deletion


def crear_categorias(apps, schema_editor):
    Producto = apps.get_model('productos', 'Producto')
    Categoria = apps.get_model('productos', 'Categoria')
    alias = schema_editor.connection.alias

    nombres = (
        Producto.objects.using(alias)
        .values_list('categoria', flat=True)
        .distinct()
    )

    for nombre in nombres:
        if nombre and nombre.strip():
            Categoria.objects.using(alias).get_or_create(
                nombre=nombre
            )


def convertir_categorias(apps, schema_editor):
    Producto = apps.get_model('productos', 'Producto')
    Categoria = apps.get_model('productos', 'Categoria')
    alias = schema_editor.connection.alias

    tabla = schema_editor.quote_name(Producto._meta.db_table)
    columna = schema_editor.quote_name(
        Producto._meta.get_field('categoria').column
    )

    categorias = Categoria.objects.using(alias).values_list(
        'nombre', 'id'
    )

    with schema_editor.connection.cursor() as cursor:
        for nombre, categoria_id in categorias:
            cursor.execute(
                f"UPDATE {tabla} SET {columna} = %s "
                f"WHERE {columna} = %s",
                [categoria_id, nombre],
            )

        cursor.execute(
            f"UPDATE {tabla} SET {columna} = NULL "
            f"WHERE {columna} = ''"
        )


class Migration(migrations.Migration):

    dependencies = [
        ('productos', '0008_categoria_alter_producto_categoria'),
    ]

    operations = [
        migrations.RunPython(
            crear_categorias,
            migrations.RunPython.noop,
        ),
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
