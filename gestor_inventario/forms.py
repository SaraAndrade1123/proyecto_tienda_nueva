# inventario/para facilitar la creacion y edicion de proveedores con valiciones de django xd
from django import forms
from .models import Proveedor

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre_empresa', 'nit', 'contacto_nombre', 'telefono', 'email', 'direccion', 'activo', 'proxima_visita']
        widgets = {
            'nombre_empresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Distribuidora Central'}),
            'nit': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. 000000000-0'}),
            'contacto_nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. Juan Pérez'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej. +57 300 123 4567'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contacto@proveedor.com'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Calle 10 # 5-20'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'proxima_visita': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        }

    def clean_nit(self):
        nit =self.cleaned_data.get('nit')
        qs = Proveedor.objects.filter(nit=nit)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Este NIT ya está registrado.")
        return nit