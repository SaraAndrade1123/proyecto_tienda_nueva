from django.apps import AppConfig


class CajaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'caja'
    # Nombre interno distinto de "caja": así sus tablas se llaman cierre_caja_... y no chocan
    # con una tabla caja_cajadiaria que ya existe en la base compartida.
    label = 'cierre_caja'
    verbose_name = 'Caja (apertura y cierre)'