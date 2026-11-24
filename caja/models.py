from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class CajaQuerySet(models.QuerySet):
    """Ni el update() ni el delete() masivos pueden tocar una caja que ya se cerró."""

    def update(self, **campos):
        if self.filter(estado=CajaDiaria.CERRADA).exists():
            raise ValidationError('Una caja cerrada no se puede modificar.')
        return super().update(**campos)

    def delete(self):
        if self.filter(estado=CajaDiaria.CERRADA).exists():
            raise ValidationError('Una caja cerrada no se puede borrar.')
        return super().delete()


class CajaDiaria(models.Model):
    """
    HU_017 / HU_018: una fila por día.
    Se crea al ABRIR la caja (con la base en efectivo) y al CERRAR se le guarda el resumen del día
    tal como estaba en ese momento: ventas, consumos, salidas y pagos a proveedores.
    Esta app solo LEE las tablas de las otras apps (Transaccion, ConsumoPersonal, SalidaProducto);
    lo único propio son esta tabla y PagoProveedor.
    """
    ABIERTA = 'abierta'
    CERRADA = 'cerrada'
    ESTADOS = [(ABIERTA, 'Abierta'), (CERRADA, 'Cerrada')]

    CUADRA = 'cuadra'
    SOBRANTE = 'sobrante'
    FALTANTE = 'faltante'
    RESULTADOS = [(CUADRA, 'Cuadró'), (SOBRANTE, 'Sobrante'), (FALTANTE, 'Faltante')]

    # ---------- Apertura ----------
    fecha = models.DateField('Día', unique=True, default=timezone.localdate)
    base_inicial = models.PositiveIntegerField('Base en efectivo')
    abierta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cajas_abiertas',
    )
    abierta_por_nombre = models.CharField('Abierta por', max_length=150, blank=True)
    abierta_en = models.DateTimeField('Abierta el', default=timezone.now, editable=False)
    estado = models.CharField(max_length=10, choices=ESTADOS, default=ABIERTA, db_index=True)

    # ---------- Resumen guardado al cerrar ("foto" del día) ----------
    ventas_total = models.PositiveBigIntegerField('Total vendido', default=0)
    ventas_cantidad = models.PositiveIntegerField('Número de ventas', default=0)
    ventas_unidades = models.PositiveIntegerField('Unidades vendidas', default=0)
    transferencias = models.PositiveBigIntegerField('Ventas por transferencia', default=0)

    consumos_total = models.PositiveBigIntegerField('Consumos personales', default=0)
    consumos_cantidad = models.PositiveIntegerField('Número de consumos', default=0)

    salidas_perdida_total = models.PositiveBigIntegerField('Salidas sin cambio (pérdida)', default=0)
    salidas_perdida_unidades = models.PositiveIntegerField('Unidades perdidas', default=0)
    salidas_cambio_total = models.PositiveBigIntegerField('Salidas con cambio del proveedor', default=0)
    salidas_cantidad = models.PositiveIntegerField('Número de salidas', default=0)

    pagos_proveedor_total = models.PositiveBigIntegerField('Pagos a proveedores', default=0)
    pagos_proveedor_cantidad = models.PositiveIntegerField('Número de pagos', default=0)

    # Puede quedar negativo si se pagó más de lo que entró (por eso no es Positive)
    esperado = models.BigIntegerField('Dinero esperado', default=0)
    contado = models.PositiveBigIntegerField('Dinero contado', null=True, blank=True)
    diferencia = models.BigIntegerField('Diferencia', null=True, blank=True)
    resultado = models.CharField(max_length=10, choices=RESULTADOS, blank=True, db_index=True)
    observacion = models.TextField('Observación', blank=True)

    cerrada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cajas_cerradas',
    )
    cerrada_por_nombre = models.CharField('Cerrada por', max_length=150, blank=True)
    cerrada_en = models.DateTimeField('Cerrada el', null=True, blank=True)

    objects = CajaQuerySet.as_manager()

    class Meta:
        verbose_name = 'Caja diaria'
        verbose_name_plural = 'Cajas diarias'
        ordering = ['-fecha']

    def __str__(self):
        return f'Caja del {self.fecha:%d/%m/%Y} ({self.get_estado_display()})'

    # ---------- Reglas ----------
    def save(self, *args, **kwargs):
        # Una vez cerrada en la base de datos, ya nadie la puede cambiar (HU_018, criterio 8)
        if not self._state.adding:
            estado_guardado = type(self).objects.filter(pk=self.pk).values_list('estado', flat=True).first()
            if estado_guardado == self.CERRADA:
                raise ValidationError('Una caja cerrada no se puede modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.estado == self.CERRADA:
            raise ValidationError('Una caja cerrada no se puede borrar.')
        return super().delete(*args, **kwargs)

    @property
    def esta_abierta(self):
        return self.estado == self.ABIERTA

    def borrar_para_pruebas(self):
        """
        SOLO para el modo de pruebas (CAJA_MODO_PRUEBAS = True en settings): borra esta caja,
        abierta o cerrada, junto con sus pagos a proveedores, para poder abrirla y cerrarla otra vez.
        Las ventas y los cobros del día NO se tocan (son de otras tablas y siguen contando).
        """
        from django.db import transaction
        with transaction.atomic():
            PagoProveedor.objects.filter(caja_id=self.pk).delete()
            # Se salta a propósito el bloqueo de «caja cerrada no se borra»
            models.QuerySet.delete(CajaDiaria.objects.filter(pk=self.pk))

    @property
    def ventas_efectivo(self):
        return self.ventas_total - self.transferencias

    @property
    def diferencia_abs(self):
        return abs(self.diferencia or 0)

    @staticmethod
    def resultado_de(diferencia):
        if diferencia == 0:
            return CajaDiaria.CUADRA
        return CajaDiaria.SOBRANTE if diferencia > 0 else CajaDiaria.FALTANTE


class PagoProveedor(models.Model):
    """
    Dinero que sale de la caja para pagarle a un proveedor ese día.
    La tabla de proveedores (gestor_inventario) no tiene un campo de dinero, por eso se anota aquí.
    Se guarda el nombre como texto para que el historial no cambie si editan o borran el proveedor.
    """
    caja = models.ForeignKey(CajaDiaria, on_delete=models.PROTECT, related_name='pagos')
    proveedor = models.ForeignKey(
        'gestor_inventario.Proveedor', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pagos_caja',
    )
    proveedor_nombre = models.CharField('Proveedor', max_length=200)
    concepto = models.CharField('Concepto', max_length=200, blank=True)
    valor = models.PositiveIntegerField('Valor pagado')
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='pagos_caja_registrados',
    )
    registrado_por_nombre = models.CharField('Registrado por', max_length=150, blank=True)
    creado_en = models.DateTimeField('Registrado el', default=timezone.now, editable=False)

    class Meta:
        verbose_name = 'Pago a proveedor'
        verbose_name_plural = 'Pagos a proveedores'
        ordering = ['creado_en', 'id']

    def __str__(self):
        return f'{self.proveedor_nombre} · ${self.valor:,}'.replace(',', '.')

    def _caja_abierta(self):
        # Se pregunta a la base de datos (no al objeto en memoria) por si la cerraron hace un momento
        return CajaDiaria.objects.filter(pk=self.caja_id, estado=CajaDiaria.ABIERTA).exists()

    def save(self, *args, **kwargs):
        if not self._caja_abierta():
            raise ValidationError('La caja de ese día ya se cerró; no se pueden cambiar sus pagos.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if not self._caja_abierta():
            raise ValidationError('La caja de ese día ya se cerró; no se pueden borrar sus pagos.')
        return super().delete(*args, **kwargs)


# ============================================================
#  COBROS DEL CARRITO (lista de productos)
# ============================================================
class CobroQuerySet(models.QuerySet):
    """Igual que las ventas: un cobro guardado no se cambia ni se borra."""

    def update(self, **campos):
        raise ValidationError('Los cobros registrados no se pueden modificar.')

    def delete(self):
        raise ValidationError('Los cobros registrados no se pueden borrar.')


class Cobro(models.Model):
    """
    Un cobro = un carrito pagado. Junta las ventas (Transaccion) que se cobraron juntas y dice
    cómo se pagaron: todo en efectivo, todo por transferencia o una parte de cada uno.
    La tabla de ventas no se toca: la unión se guarda en CobroItem.
    """
    EFECTIVO = 'efectivo'
    TRANSFERENCIA = 'transferencia'
    MIXTO = 'mixto'
    METODOS = [(EFECTIVO, 'Efectivo'), (TRANSFERENCIA, 'Transferencia'), (MIXTO, 'Efectivo y transferencia')]

    metodo = models.CharField('Cómo pagó', max_length=15, choices=METODOS)
    total = models.PositiveBigIntegerField('Total')
    # Lo que de verdad queda en el cajón (si pagó con un billete grande, ya sin el vuelto)
    efectivo = models.PositiveBigIntegerField('Efectivo', default=0)
    transferencia = models.PositiveBigIntegerField('Transferencia', default=0)
    recibido = models.PositiveBigIntegerField('Con cuánto pagó', null=True, blank=True)
    vuelto = models.PositiveBigIntegerField('Vuelto', default=0)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='cobros_registrados',
    )
    registrado_por_nombre = models.CharField('Registrado por', max_length=150, blank=True)
    creado_en = models.DateTimeField('Cobrado el', default=timezone.now, editable=False, db_index=True)

    objects = CobroQuerySet.as_manager()

    class Meta:
        verbose_name = 'Cobro'
        verbose_name_plural = 'Cobros'
        ordering = ['-creado_en', '-id']

    def __str__(self):
        return f'Cobro #{self.pk} · ${self.total:,} ({self.get_metodo_display()})'.replace(',', '.')

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError('Los cobros registrados no se pueden modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('Los cobros registrados no se pueden borrar.')


class CobroItem(models.Model):
    """Une cada venta con el cobro en que se pagó (una venta solo puede estar en un cobro)."""
    cobro = models.ForeignKey(Cobro, on_delete=models.PROTECT, related_name='items')
    transaccion = models.OneToOneField(
        'productos.Transaccion', on_delete=models.PROTECT, related_name='cobro_item',
    )

    class Meta:
        verbose_name = 'Venta del cobro'
        verbose_name_plural = 'Ventas del cobro'

    def __str__(self):
        return f'{self.cobro} -> {self.transaccion}'