from django import forms

from .models import Producto, Categoria


class ProductoForm(forms.ModelForm):

    class Meta:
        model = Producto

        fields = [
            'nombre',
            'precio_unitario',
            'cantidad',
            'unidad_medida',
            'categoria',
            'existencias',
            'imagen',
            'descripcion',
        ]

        widgets = {
            'nombre': forms.TextInput(
                attrs={
                    'placeholder': 'Ej: Leche entera'
                }
            ),

            'precio_unitario': forms.NumberInput(
                attrs={
                    'placeholder': 'Ej: 45000'
                }
            ),

            'cantidad': forms.NumberInput(
                attrs={
                    'placeholder': 'Ej: 1, 10, 500...'
                }
            ),

            'existencias': forms.NumberInput(
                attrs={
                    'placeholder': 'Ej: 20'
                }
            ),

            'descripcion': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': (
                        'Describe el producto: origen, '
                        'características, usos...'
                    ),
                }
            ),
        }


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'placeholder': 'Ej: Lácteos',
                'autocomplete': 'off'
            })
        }

    def clean_nombre(self):
        nombre = self.cleaned_data['nombre'].strip()

        if not nombre:
            raise forms.ValidationError(
                'El nombre de la categoría es obligatorio.'
            )

        categorias = Categoria.objects.filter(nombre__iexact=nombre)

        if self.instance.pk:
            categorias = categorias.exclude(pk=self.instance.pk)

        if categorias.exists():
            raise forms.ValidationError(
                'Ya existe una categoría con ese nombre.'
            )

        return nombre