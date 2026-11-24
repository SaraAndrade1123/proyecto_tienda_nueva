import re

from django import forms

from gestor_inventario.models import Proveedor

TOPE = 999_999_999   # nadie maneja más de esto en la caja de una tienda


class PesosField(forms.CharField):
    """
    Pesos colombianos ENTEROS (sin decimales). Acepta lo que la gente escribe de verdad:
    «50000», «50.000», «$ 50.000». Lo que no se acepta: comas, letras o números negativos.
    """

    def __init__(self, *args, minimo=0, maximo=TOPE, **kwargs):
        self.minimo, self.maximo = minimo, maximo
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs.update({'inputmode': 'numeric', 'autocomplete': 'off', 'data-pesos': ''})
        return attrs

    def to_python(self, value):
        texto = super().to_python(value).replace('$', '').replace(' ', '').replace('\xa0', '')
        if texto in self.empty_values:
            return None
        if len(texto) > 20:
            raise forms.ValidationError('Ese valor es demasiado largo.')
        if texto.startswith('-'):
            raise forms.ValidationError('El valor no puede ser negativo.')
        if ',' in texto:
            raise forms.ValidationError('Escribe el valor en pesos, sin decimales (ej: 50000 o 50.000).')
        # Puntos solo como separador de miles: 50.000 o 1.250.000
        if '.' in texto and not re.fullmatch(r'\d{1,3}(\.\d{3})+', texto):
            raise forms.ValidationError('Escribe el valor en pesos, sin decimales (ej: 50000 o 50.000).')
        texto = texto.replace('.', '')
        if not texto.isdigit():
            raise forms.ValidationError('Escribe solo números.')
        return int(texto)

    def validate(self, value):
        super().validate(value)
        if value is None:
            return
        if value < self.minimo:
            raise forms.ValidationError(f'El valor debe ser mayor o igual a ${self.minimo:,}.'.replace(',', '.'))
        if value > self.maximo:
            raise forms.ValidationError(f'El valor no puede pasar de ${self.maximo:,}.'.replace(',', '.'))


# ============================================================
#  HU_017 · Apertura
# ============================================================
class AperturaForm(forms.Form):
    base_inicial = PesosField(
        label='¿Con cuánto empieza la caja?',
        widget=forms.TextInput(attrs={'placeholder': '0', 'autofocus': True}),
        maximo=50_000_000,
        error_messages={'required': 'Escribe con cuánto dinero empieza la caja (puede ser 0).'},
    )


# ============================================================
#  Pagos a proveedores (salen del cajón)
# ============================================================
class PagoForm(forms.Form):
    OTRO = 'otro'

    proveedor = forms.CharField(required=False)   # id de un proveedor activo o «otro»
    otro_nombre = forms.CharField(label='¿A quién se le pagó?', required=False, max_length=200)
    concepto = forms.CharField(label='Concepto', required=False, max_length=200)
    valor = PesosField(
        label='Valor pagado', minimo=1, maximo=50_000_000,
        error_messages={'required': 'Escribe cuánto se pagó.'},
    )

    def __init__(self, *args, disponible=None, **kwargs):
        self.disponible = disponible
        super().__init__(*args, **kwargs)
        self.proveedores = Proveedor.objects.filter(activo=True).order_by('nombre_empresa')

    def clean_proveedor(self):
        valor = (self.cleaned_data.get('proveedor') or '').strip()
        if valor in ('', self.OTRO):
            return valor
        if not valor.isdigit():
            raise forms.ValidationError('Elige un proveedor de la lista.')
        proveedor = self.proveedores.filter(pk=int(valor)).first()
        if proveedor is None:
            raise forms.ValidationError('Ese proveedor no existe o está inactivo.')
        return proveedor

    def clean(self):
        datos = super().clean()
        proveedor = datos.get('proveedor')
        nombre = (datos.get('otro_nombre') or '').strip()
        if 'proveedor' in self.errors:
            return datos
        if proveedor == '':
            self.add_error('proveedor', 'Elige a qué proveedor se le pagó.')
        elif proveedor == self.OTRO and not nombre:
            self.add_error('otro_nombre', 'Escribe a quién se le pagó.')
        valor = datos.get('valor')
        if valor and self.disponible is not None and valor > self.disponible:
            self.add_error('valor', 'Ese valor es más de lo que hay en efectivo en la caja. Revisa el valor.')
        return datos

    def proveedor_y_nombre(self):
        proveedor = self.cleaned_data['proveedor']
        if proveedor == self.OTRO:
            return None, self.cleaned_data['otro_nombre'].strip()
        return proveedor, proveedor.nombre_empresa


# ============================================================
#  HU_018 · Cierre
# ============================================================
class CierreForm(forms.Form):
    # Las transferencias NO se escriben: salen solas de los cobros del carrito.
    # Una venta que no pasó por el carrito se cuenta como efectivo.
    contado = PesosField(
        label='¿Cuánto dinero hay en la caja?',
        widget=forms.TextInput(attrs={'placeholder': '0'}),
        error_messages={'required': 'Escribe cuánto dinero contaste (puede ser 0).'},
    )
    observacion = forms.CharField(
        label='Observación', required=False, max_length=1000,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, resumen=None, **kwargs):
        self.resumen = resumen
        super().__init__(*args, **kwargs)

    def clean(self):
        datos = super().clean()
        contado = datos.get('contado')
        if contado is None:
            return datos
        esperado = self.resumen['esperado_ahora']
        diferencia = contado - esperado
        datos['transferencias'] = 0
        datos['transferencias_total'] = self.resumen['cobros_transferencia']
        datos['esperado'] = esperado
        datos['diferencia'] = diferencia
        datos['diferencia_abs'] = abs(diferencia)
        observacion = (datos.get('observacion') or '').strip()
        datos['observacion'] = observacion
        # HU_018, criterio 6: si no cuadra, hay que explicar por qué
        if diferencia != 0 and len(observacion) < 5:
            self.add_error(
                'observacion',
                'Hay sobrante o faltante: cuenta qué pudo pasar (mínimo 5 letras).',
            )
        return datos