"""DAO de solicitudes de reposición (sección 4.9.3)."""

from .models import SolicitudReposicion


class ReposicionDAO:
    def insertar(self, **campos):
        return SolicitudReposicion.objects.create(**campos)

    def actualizar(self, solicitud):
        solicitud.save()

    def _base(self):
        return SolicitudReposicion.objects.select_related("repuesto", "centro", "centro_origen", "orden",
                                                          "solicitante", "revisor")

    def buscar_por_codigo(self, codigo, con_bloqueo=False):
        qs = SolicitudReposicion.objects.select_for_update() if con_bloqueo else self._base()
        return qs.filter(codigo=codigo).first()

    def listar_por_estado(self, estados, centro_id=None):
        qs = self._base().filter(estado__in=estados)
        if centro_id:
            qs = qs.filter(centro_id=centro_id)
        return list(qs)

    def listar_por_orden(self, orden_id):
        return list(self._base().filter(orden_id=orden_id))

    def listar_todas(self):
        return list(self._base())

    def ultimo_codigo(self):
        ultima = SolicitudReposicion.objects.order_by("-id").first()
        return ultima.codigo if ultima else None
