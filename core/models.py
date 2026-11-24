from django.conf import settings
from django.db import models


class PerfilEmpleado(models.Model):
    """Centro al que pertenece un técnico o almacenero. El coordinador puede no tener centro."""

    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil")
    centro = models.ForeignKey("inventario.CentroServicio", null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        verbose_name = "perfil de empleado"
        verbose_name_plural = "perfiles de empleado"

    def __str__(self):
        return f"{self.usuario} – {self.centro or 'todos los centros'}"


class Bitacora(models.Model):
    """Registro de cada cambio de órdenes e inventario (RF-16, RN-05, RNF-07)."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True)
    operacion = models.CharField(max_length=60)
    referencia = models.CharField(max_length=60, help_text="Código de la orden o solicitud")
    detalle = models.TextField(blank=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "registro de bitácora"
        verbose_name_plural = "bitácora"

    def __str__(self):
        return f"{self.fecha:%Y-%m-%d %H:%M} {self.operacion} {self.referencia}"


class Aviso(models.Model):
    """Aviso enviado al cliente cuando cambia el estado o la fecha de su orden (RF-06)."""

    cliente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="avisos")
    referencia = models.CharField(max_length=30)
    asunto = models.CharField(max_length=150)
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    leido = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.referencia}: {self.asunto}"
