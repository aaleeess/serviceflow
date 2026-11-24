"""DAO de órdenes (sección 4.9.3)."""

from .models import Diagnostico, HistorialEstado, OrdenReparacion


class OrdenDAO:
    def insertar(self, **campos):
        return OrdenReparacion.objects.create(**campos)

    def actualizar(self, orden, campos):
        orden.save(update_fields=list(campos) + ["actualizada"])

    def _base(self):
        return OrdenReparacion.objects.select_related("cliente", "centro", "diagnostico__repuesto")

    def buscar_por_codigo(self, codigo):
        return self._base().filter(codigo=codigo).first()

    def buscar_por_codigo_con_bloqueo(self, codigo):
        return OrdenReparacion.objects.select_for_update().filter(codigo=codigo).first()

    def buscar_por_cliente(self, cliente_id):
        return list(self._base().filter(cliente_id=cliente_id).order_by("-codigo"))

    def listar(self, centro_id=None, estados=None):
        qs = self._base()
        if centro_id:
            qs = qs.filter(centro_id=centro_id)
        if estados:
            qs = qs.filter(estado__in=estados)
        return list(qs)

    def ultimo_codigo(self):
        ultima = OrdenReparacion.objects.order_by("-id").first()
        return ultima.codigo if ultima else None


class DiagnosticoDAO:
    def insertar(self, **campos):
        return Diagnostico.objects.create(**campos)


class HistorialDAO:
    def insertar(self, **campos):
        return HistorialEstado.objects.create(**campos)

    def listar_por_orden(self, orden_id):
        return list(HistorialEstado.objects.filter(orden_id=orden_id))
