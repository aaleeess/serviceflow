"""Avisos al cliente (RF-06).

Cada aviso queda guardado en la tabla Aviso (el cliente lo ve en "Avisos") y además se
envía por correo. En el piloto el correo se imprime en la ventana del servidor (backend de
consola). Es el componente de avisos "simulado" del diagrama de componentes (5.3).
"""

from dataclasses import dataclass
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail

from .repositories import AvisoRepository


@dataclass(frozen=True)
class AvisoDTO:
    """Lo que el cliente ve de cada aviso."""

    referencia: str
    asunto: str
    mensaje: str
    fecha: datetime
    nuevo: bool


class AvisoService:
    def __init__(self, repo=None):
        self.repo = repo or AvisoRepository()

    def notificar(self, orden, asunto, mensaje):
        cliente = orden.cliente
        self.repo.guardar(cliente, orden.codigo, asunto, mensaje)
        if cliente.email:
            # Un fallo del correo no debe deshacer la operación que originó el aviso.
            send_mail(f"[ServiceFlow] {orden.codigo}: {asunto}", mensaje,
                      settings.DEFAULT_FROM_EMAIL, [cliente.email], fail_silently=True)

    def avisos_de(self, cliente, referencia=None, marcar_leidos=False):
        avisos = self.repo.de_cliente(cliente.id, referencia)
        dtos = [AvisoDTO(a.referencia, a.asunto, a.mensaje, a.fecha, not a.leido) for a in avisos]
        if marcar_leidos:
            self.repo.marcar_leidos(cliente.id, avisos)
        return dtos

    def cuantos_nuevos(self, cliente):
        return self.repo.no_leidos(cliente.id)
