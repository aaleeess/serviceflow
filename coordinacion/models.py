from django.conf import settings
from django.db import models


class EstadoSolicitud:
    PENDIENTE = "PENDIENTE"
    AUTORIZADA = "AUTORIZADA"
    RECHAZADA = "RECHAZADA"
    ATENDIDA = "ATENDIDA"

    CHOICES = [
        (PENDIENTE, "Pendiente de autorización"),
        (AUTORIZADA, "Autorizada"),
        (RECHAZADA, "Rechazada"),
        (ATENDIDA, "Atendida"),
    ]


class TipoSolicitud:
    REPOSICION = "REPOSICION"
    TRASLADO = "TRASLADO"

    CHOICES = [(REPOSICION, "Reposición"), (TRASLADO, "Traslado")]


class SolicitudReposicion(models.Model):
    """Pedido de abastecimiento o de traslado entre centros (RF-12, CU-10)."""

    codigo = models.CharField(max_length=20, unique=True)
    orden = models.ForeignKey("ordenes.OrdenReparacion", null=True, blank=True, on_delete=models.PROTECT,
                              related_name="solicitudes")
    tipo = models.CharField(max_length=20, choices=TipoSolicitud.CHOICES, default=TipoSolicitud.REPOSICION)
    repuesto = models.ForeignKey("inventario.Repuesto", on_delete=models.PROTECT)
    centro = models.ForeignKey("inventario.CentroServicio", on_delete=models.PROTECT,
                               help_text="Centro que recibe el repuesto")
    centro_origen = models.ForeignKey("inventario.CentroServicio", null=True, blank=True,
                                      on_delete=models.PROTECT, related_name="+",
                                      help_text="Solo en traslados: centro que entrega el repuesto")
    cantidad = models.PositiveIntegerField()
    estado = models.CharField(max_length=20, choices=EstadoSolicitud.CHOICES, default=EstadoSolicitud.PENDIENTE)
    motivo_decision = models.CharField(max_length=200, blank=True)
    solicitante = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    revisor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT,
                                related_name="+")
    creada = models.DateTimeField(auto_now_add=True)
    resuelta = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creada", "-id"]
        verbose_name = "solicitud de reposición"
        verbose_name_plural = "solicitudes de reposición"

    def __str__(self):
        return f"{self.codigo} – {self.repuesto} x{self.cantidad}"
