from django import forms
from django.conf import settings
from django.utils import timezone

from productos.models import Producto
from .models import MotivoSalida, SalidaProducto

FOTO_MAX_MB = 5


def fotos_habilitadas():
    """La foto de evidencia se puede apagar con SALIDAS_PERMITIR_FOTO = False en settings.py."""
    return getattr(settings, 'SALIDAS_PERMITIR_FOTO', True)


class SalidaForm(forms.ModelForm):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(existencias__gt=0),
        empty_label='Elige el producto',
        error_messages={'required': 'Elige el producto que sale del inventario.',
                        'invalid_choice': 'Ese producto no existe o ya no tiene existencias.'},
    )
    cantidad = forms.IntegerField(
        min_value=1,
        error_messages={'required': 'Escribe cuántas unidades salen.',
                        'min_value': 'La cantidad debe ser mayor que cero.',
                        'invalid': 'Escribe un número entero.'},
        widget=forms.TextInput(attrs={'inputmode': 'numeric', 'pattern': '[0-9]*', 'autocomplete': 'off', 'placeholder': 'Ej: 2'}),
    )
    motivo = forms.ModelChoiceField(
        queryset=MotivoSalida.objects.all(),
        empty_label=None,
        widget=forms.RadioSelect,
        error_messages={'required': 'Elige el motivo de la baja.',
                        'invalid_choice': 'Ese motivo ya no existe. Elige otro.'},
    )

    class Meta:
        model = SalidaProducto
        fields = ['producto', 'cantidad', 'motivo', 'fecha', 'descripcion', 'observaciones_recepcion', 'foto']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'descripcion': forms.Textarea(attrs={'rows': 3, 'placeholder': '¿Qué pasó? Ej: Se cayó una caja al descargar y se rompieron 2 frascos.'}),
            'observaciones_recepcion': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Ej: Empaque roto, envase abierto, llegaron 10 de 12.'}),
            'foto': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }
        error_messages = {
            'descripcion': {'required': 'Describe lo que sucedió.'},
            'fecha': {'required': 'Indica la fecha de la baja.', 'invalid': 'Escribe una fecha válida.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.filter(existencias__gt=0)
        self.fields['producto'].label_from_instance = lambda p: f'{p.nombre} · quedan {p.existencias}'
        self.fields['fecha'].initial = timezone.localdate
        if not fotos_habilitadas():
            del self.fields['foto']

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        if fecha > timezone.localdate():
            raise forms.ValidationError('La fecha de la baja no puede ser futura.')
        return fecha

    def clean_foto(self):
        foto = self.cleaned_data.get('foto')
        if foto and hasattr(foto, 'size') and foto.size > FOTO_MAX_MB * 1024 * 1024:
            raise forms.ValidationError(f'La foto pesa más de {FOTO_MAX_MB} MB.')
        return foto

    def clean(self):
        datos = super().clean()
        producto, cantidad = datos.get('producto'), datos.get('cantidad')
        if producto and cantidad and cantidad > producto.existencias:
            self.add_error('cantidad', f'No alcanza: de {producto.nombre} solo quedan {producto.existencias}.')
        return datos


class MotivoForm(forms.ModelForm):
    class Meta:
        model = MotivoSalida
        fields = ['nombre', 'da_cambio']
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Ej: Consumo de la casa', 'maxlength': 80, 'autocomplete': 'off'}),
        }
        error_messages = {
            'nombre': {'required': 'Escribe el nombre del motivo.', 'unique': 'Ya existe un motivo con ese nombre.'},
        }

    def clean_nombre(self):
        nombre = ' '.join(self.cleaned_data['nombre'].split())   # quita espacios de más
        if not nombre:
            raise forms.ValidationError('Escribe el nombre del motivo.')
        repetido = MotivoSalida.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if repetido.exists():
            raise forms.ValidationError('Ya existe un motivo con ese nombre.')
        return nombre