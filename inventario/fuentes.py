"""Fuentes de inventario y patrón estructural Adapter (secciones 4.3 y 4.9.2).

FuenteInventario es el contrato. InventarioRepository (la base de datos del piloto) y
InventarioExternoAdapter (un futuro sistema autorizado) lo implementan, así el servicio
de reservas no cambia si mañana se conecta otra fuente.
"""

from abc import ABC, abstractmethod


class FuenteInventario(ABC):
    @abstractmethod
    def disponibilidad_por_centro(self, repuesto_id):
        """Devuelve [(nombre_centro, centro_id, disponible), ...]."""


class SimuladorInventarioExterno:
    """Simula un servicio externo con otra forma de responder (no es un sistema real de Samsung)."""

    def consultar_stock(self, sku):
        return {"sku": sku, "almacenes": []}


class InventarioExternoAdapter(FuenteInventario):
    """Traduce la respuesta del servicio externo al contrato FuenteInventario."""

    def __init__(self, servicio=None, repuestos=None):
        self.servicio = servicio or SimuladorInventarioExterno()
        self.repuestos = repuestos  # función repuesto_id -> código de pieza

    def disponibilidad_por_centro(self, repuesto_id):
        sku = self.repuestos(repuesto_id) if self.repuestos else str(repuesto_id)
        respuesta = self.servicio.consultar_stock(sku)
        return [(a["nombre"], a.get("id"), int(a["libres"])) for a in respuesta.get("almacenes", [])]
