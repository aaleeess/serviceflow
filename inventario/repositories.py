"""Repositorios de inventario (sección 4.9.2): operaciones con sentido de negocio."""

from .daos import CentroDAO, InventarioDAO, MovimientoDAO, RepuestoDAO, ReservaDAO
from .fuentes import FuenteInventario


class InventarioRepository(FuenteInventario):
    def __init__(self, dao=None):
        self.dao = dao or InventarioDAO()

    def obtener_con_bloqueo(self, repuesto_id, centro_id, crear=False):
        inv = self.dao.buscar_con_bloqueo(repuesto_id, centro_id)
        if inv is None and crear:
            self.dao.crear(repuesto_id, centro_id)
            inv = self.dao.buscar_con_bloqueo(repuesto_id, centro_id)
        return inv

    def obtener(self, repuesto_id, centro_id):
        return self.dao.buscar(repuesto_id, centro_id)

    def del_centro(self, centro_id):
        return self.dao.listar_por_centro(centro_id)

    def todo(self):
        return self.dao.listar_todo()

    def disponibilidad_por_centro(self, repuesto_id):
        return [(i.centro.nombre, i.centro_id, i.disponible) for i in self.dao.listar_por_repuesto(repuesto_id)]

    def guardar(self, inventario):
        self.dao.actualizar(inventario)


class ReservaRepository:
    def __init__(self, dao=None):
        self.dao = dao or ReservaDAO()

    def guardar(self, **campos):
        return self.dao.insertar(**campos)

    def buscar_por_orden(self, orden_id):
        return self.dao.listar_por_orden(orden_id)

    def activas_del_centro(self, centro_id):
        return self.dao.listar_activas_por_centro(centro_id)

    def marcar_consumida(self, reserva):
        reserva.consumida = True
        self.dao.actualizar(reserva)


class MovimientoRepository:
    def __init__(self, dao=None):
        self.dao = dao or MovimientoDAO()

    def registrar(self, inventario, tipo, cantidad, usuario, motivo="", referencia=""):
        return self.dao.insertar(inventario=inventario, tipo=tipo, cantidad=cantidad, usuario=usuario,
                                 motivo=motivo, referencia=referencia)

    def del_centro(self, centro_id, limite=40):
        return self.dao.listar_por_centro(centro_id, limite)


class CatalogoRepository:
    def __init__(self, centros=None, repuestos=None):
        self.centros = centros or CentroDAO()
        self.repuestos = repuestos or RepuestoDAO()

    def listar_centros(self):
        return self.centros.listar()

    def centro(self, centro_id):
        return self.centros.buscar_por_id(centro_id)

    def listar_repuestos(self):
        return self.repuestos.listar()

    def repuesto(self, repuesto_id):
        return self.repuestos.buscar_por_id(repuesto_id)
