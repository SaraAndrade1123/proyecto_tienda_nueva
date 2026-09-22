from django import forms
from .models import Producto


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'precio_unitario', 'cantidad', 'unidad_medida', 'categoria', 'existencias', 'imagen']
        
        
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Leche entera'}),
            'precio_unitario': forms.NumberInput(attrs={'placeholder': 'Ej: 45000'}),
            'cantidad': forms.NumberInput(attrs={'placeholder': 'Ej: 1, 10, 500...'}),
            'existencias': forms.NumberInput(attrs={'placeholder': 'Ej: 20'}),
        }