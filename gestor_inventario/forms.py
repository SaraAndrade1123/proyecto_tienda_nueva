
from django import forms
from .models import Proveedor


class ProveedorForm(forms.ModelForm):

    class Meta:
        model = Proveedor
        fields = [
            'nombre',
            'nit',
            'telefono_contacto',
            'correo',
        ]

        widgets = {
            'nombre': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del proveedor',
                'required': True,
            }),
            'nit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'NIT del proveedor',
                'required': True,
            }),
            'telefono_contacto': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Teléfono de contacto',
                'required': True,
            }),
            'correo': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@proveedor.com',
                'required': True,
            }),
        }

    def clean_nit(self):
        nit = self.cleaned_data.get('nit')

        proveedores = Proveedor.objects.filter(nit=nit)

        if self.instance.pk:
            proveedores = proveedores.exclude(pk=self.instance.pk)

        if proveedores.exists():
            raise forms.ValidationError(
                'El usuario ya está registrado.'
            )

        return nit
