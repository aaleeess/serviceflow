from django.conf import settings
from django.db import models
from django.db.models import F, Q


class CentroServicio(models.Model):
    """Centro de servicio del piloto (datos ficticios, sección 2.1)."""

    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=150, blank=True)
    horario_atencion = models.CharField(max_length=100)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "centro de servicio"
        verbose_name_plural = "centros de servicio"

    def __str__(self):
        return self.nombre


class Repuesto(models.Model):
    codigo_pieza = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=120)
    compatibilidad = models.CharField(max_length=200, help_text="Modelos compatibles, separados por coma")

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @staticmethod
    def normalizar_modelo(texto):
        """'Samsung Galaxy A55 5G' → 'galaxy a55'. Así 'Galaxy S24' no se confunde con 'Galaxy S24 Ultra'."""
        partes = [p for p in texto.lower().replace("-", " ").split() if p not in ("samsung", "5g", "4g", "lte")]
        return " ".join(partes)

    def es_compatible(self, modelo_equipo):
        """RF-08: el repuesto debe corresponder exactamente al modelo del equipo."""
        modelo = self.normalizar_modelo(modelo_equipo)
        return any(self.normalizar_modelo(m) == modelo for m in self.compatibilidad.split(",") if m.strip())


class Inventario(models.Model):
    """Stock de un repuesto en un centro: un registro por cada par repuesto–centro."""

    repuesto = models.ForeignKey(Repuesto, on_delete=models.PROTECT, related_name="inventarios")
    centro = models.ForeignKey(CentroServicio, on_delete=models.PROTECT, related_name="inventarios")
    stock_fisico = models.PositiveIntegerField(default=0)
    stock_reservado = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name_plural = "inventario"
        constraints = [
            models.UniqueConstraint(fields=["repuesto", "centro"], name="inventario_unico_por_centro"),
            # RNF-06: el disponible nunca puede ser negativo
            models.CheckConstraint(condition=Q(stock_reservado__lte=F("stock_fisico")),
                                   name="reservado_no_supera_fisico"),
        ]

    @property
    def disponible(self):
        """RN-02: disponible = stock físico − stock reservado. Es un valor derivado, no se guarda."""
        return self.stock_fisico - self.stock_reservado

    def __str__(self):
        return f"{self.repuesto} en {self.centro}"


class Reserva(models.Model):
    orden = models.ForeignKey("ordenes.OrdenReparacion", on_delete=models.PROTECT, related_name="reservas")
    inventario = models.ForeignKey(Inventario, on_delete=models.PROTECT, related_name="reservas")
    cantidad = models.PositiveIntegerField()
    fecha = models.DateTimeField(auto_now_add=True)
    registrada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    consumida = models.BooleanField(default=False, help_text="True cuando la pieza se usó en la reparación")

    def __str__(self):
        return f"Reserva de {self.cantidad} para {self.orden.codigo}"


class TipoMovimiento:
    INGRESO = "INGRESO"
    CONSUMO = "CONSUMO"
    AJUSTE = "AJUSTE"
    TRASLADO_SALIDA = "TRASLADO_SALIDA"
    TRASLADO_ENTRADA = "TRASLADO_ENTRADA"

    CHOICES = [
        (INGRESO, "Ingreso por reposición"),
        (CONSUMO, "Consumo en reparación"),
        (AJUSTE, "Ajuste autorizado"),
        (TRASLADO_SALIDA, "Salida por traslado"),
        (TRASLADO_ENTRADA, "Entrada por traslado"),
    ]


class MovimientoInventario(models.Model):
    """Cada cambio del stock físico (RF-11, RNF-07)."""

    inventario = models.ForeignKey(Inventario, on_delete=models.PROTECT, related_name="movimientos")
    tipo = models.CharField(max_length=20, choices=TipoMovimiento.CHOICES)
    cantidad = models.IntegerField(help_text="Positiva si entra stock, negativa si sale")
    motivo = models.CharField(max_length=200, blank=True)
    referencia = models.CharField(max_length=30, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"

    def __str__(self):
        return f"{self.get_tipo_display()} {self.cantidad:+d} · {self.inventario.repuesto}"
