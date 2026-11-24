"""DAO de inventario (sección 4.9.3). Envuelven a los Managers del ORM de Django."""

from .models import CentroServicio, Inventario, MovimientoInventario, Repuesto, Reserva


class CentroDAO:
    def listar(self):
        return list(CentroServicio.objects.all())

    def buscar_por_id(self, centro_id):
        return CentroServicio.objects.filter(pk=centro_id).first()


class RepuestoDAO:
    def listar(self):
        return list(Repuesto.objects.all())

    def buscar_por_id(self, repuesto_id):
        return Repuesto.objects.filter(pk=repuesto_id).first()


class InventarioDAO:
    def buscar_con_bloqueo(self, repuesto_id, centro_id):
        """El único lugar con SELECT ... FOR UPDATE (reserva atómica, sección 2.7)."""
        return (Inventario.objects.select_for_update()
                .filter(repuesto_id=repuesto_id, centro_id=centro_id).first())

    def buscar(self, repuesto_id, centro_id):
        return (Inventario.objects.select_related("repuesto", "centro")
                .filter(repuesto_id=repuesto_id, centro_id=centro_id).first())

    def crear(self, repuesto_id, centro_id):
        return Inventario.objects.create(repuesto_id=repuesto_id, centro_id=centro_id)

    def listar_por_centro(self, centro_id):
        return list(Inventario.objects.select_related("repuesto", "centro")
                    .filter(centro_id=centro_id).order_by("repuesto__nombre"))

    def listar_por_repuesto(self, repuesto_id):
        return list(Inventario.objects.select_related("centro").filter(repuesto_id=repuesto_id)
                    .order_by("centro__nombre"))

    def listar_todo(self):
        return list(Inventario.objects.select_related("repuesto", "centro"))

    def actualizar(self, inventario):
        inventario.save(update_fields=["stock_fisico", "stock_reservado"])


class ReservaDAO:
    def insertar(self, **campos):
        return Reserva.objects.create(**campos)

    def listar_por_orden(self, orden_id):
        return list(Reserva.objects.select_related("inventario").filter(orden_id=orden_id))

    def listar_activas_por_centro(self, centro_id):
        return list(Reserva.objects.select_related("orden").filter(inventario__centro_id=centro_id,
                                                                   consumida=False))

    def actualizar(self, reserva):
        reserva.save(update_fields=["consumida"])


class MovimientoDAO:
    def insertar(self, **campos):
        return MovimientoInventario.objects.create(**campos)

    def listar_por_centro(self, centro_id, limite=40):
        return list(MovimientoInventario.objects.select_related("inventario__repuesto", "usuario")
                    .filter(inventario__centro_id=centro_id)[:limite])
