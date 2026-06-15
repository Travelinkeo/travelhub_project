from django.db import models

class Aeropuerto(models.Model):
    """
    Modelo para almacenar aeropuertos a nivel global.
    Permite codificación/decodificación IATA y búsquedas de cercanía geográfica.
    """
    codigo_iata = models.CharField(max_length=3, unique=True, db_index=True, verbose_name="Código IATA")
    nombre = models.CharField(max_length=150, verbose_name="Nombre del Aeropuerto")
    ciudad = models.CharField(max_length=150, db_index=True, verbose_name="Ciudad")
    pais = models.CharField(max_length=100, db_index=True, verbose_name="País")
    pais_codigo = models.CharField(max_length=2, db_index=True, verbose_name="Código de País")
    latitud = models.FloatField(verbose_name="Latitud")
    longitud = models.FloatField(verbose_name="Longitud")
    es_principal = models.BooleanField(default=False, verbose_name="¿Es Aeropuerto Principal?")

    class Meta:
        verbose_name = "Aeropuerto"
        verbose_name_plural = "Aeropuertos"
        ordering = ["pais", "ciudad", "nombre"]

    def __str__(self):
        return f"{self.codigo_iata} - {self.nombre} ({self.ciudad}, {self.pais})"
