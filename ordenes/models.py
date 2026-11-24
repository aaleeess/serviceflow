from django.conf import settings
from django.db import models

from core.configuracion import EstadoOrden


class OrdenReparacion(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ordenes")
    centro = models.ForeignKey("inventario.CentroServicio", on_delete=models.PROTECT, related_name="ordenes")
    modelo_equipo = models.CharField(max_length=100)
    falla_reportada = models.TextField()
    estado = models.CharField(max_length=30, choices=EstadoOrden.CHOICES, default=EstadoOrden.RECIBIDA)
    fecha_estimada = models.DateField(null=True, blank=True,
                                      help_text="Solo se muestra al cliente cuando el técnico la confirma")
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["codigo"]
        verbose_name = "orden de reparación"
        verbose_name_plural = "órdenes de reparación"

    def __str__(self):
        return f"{self.codigo} – {self.modelo_equipo}"


class Diagnostico(models.Model):
    orden = models.OneToOneField(OrdenReparacion, on_delete=models.CASCADE, related_name="diagnostico")
    tecnico = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    descripcion = models.TextField()
    repuesto = models.ForeignKey("inventario.Repuesto", null=True, blank=True, on_delete=models.PROTECT,
                                 help_text="Vacío si la reparación no requiere repuesto")
    cantidad = models.PositiveIntegerField(default=1)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Diagnóstico de {self.orden.codigo}"


class HistorialEstado(models.Model):
    """Cada paso de la orden, con texto pensado para el cliente (RF-14)."""

    orden = models.ForeignKey(OrdenReparacion, on_delete=models.CASCADE, related_name="historial")
    estado_anterior = models.CharField(max_length=30, blank=True)
    estado_nuevo = models.CharField(max_length=30, choices=EstadoOrden.CHOICES)
    descripcion = models.CharField(max_length=200)
    motivo = models.CharField(max_length=200, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "id"]
        verbose_name_plural = "historial de estados"

    def __str__(self):
        return f"{self.orden.codigo}: {self.descripcion}"
