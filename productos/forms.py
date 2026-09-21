from django import forms
from .models import Producto


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
        ]