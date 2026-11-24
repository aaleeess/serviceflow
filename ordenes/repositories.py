"""Repositorio de órdenes (sección 4.9.2)."""

from core.configuracion import ConfiguracionSistema

from .daos import DiagnosticoDAO, HistorialDAO, OrdenDAO


class OrdenRepository:
    def __init__(self, ordenes=None, historial=None, diagnosticos=None):
        self.ordenes = ordenes or OrdenDAO()
        self.historial = historial or HistorialDAO()
        self.diagnosticos = diagnosticos or DiagnosticoDAO()

    def buscar_por_codigo(self, codigo, con_bloqueo=False):
        if con_bloqueo:
            return self.ordenes.buscar_por_codigo_con_bloqueo(codigo)
        return self.ordenes.buscar_por_codigo(codigo)

    def buscar_por_cliente(self, cliente_id):
        """RN-06: el cliente solo obtiene sus propias órdenes."""
        return self.ordenes.buscar_por_cliente(cliente_id)

    def listar(self, centro_id=None, estados=None):
        return self.ordenes.listar(centro_id, estados)

    def historial_de(self, orden):
        return self.historial.listar_por_orden(orden.id)

    def siguiente_codigo(self):
        prefijo = ConfiguracionSistema().prefijo_orden
        ultimo = self.ordenes.ultimo_codigo()
        numero = int(ultimo.replace(prefijo, "")) + 1 if ultimo else 1
        return f"{prefijo}{numero:05d}"

    def guardar_nueva(self, **campos):
        return self.ordenes.insertar(**campos)

    def actualizar(self, orden, *campos):
        self.ordenes.actualizar(orden, campos)

    def registrar_historial(self, orden, anterior, nuevo, descripcion, usuario, motivo=""):
        return self.historial.insertar(orden=orden, estado_anterior=anterior, estado_nuevo=nuevo,
                                       descripcion=descripcion, usuario=usuario, motivo=motivo)

    def guardar_diagnostico(self, **campos):
        return self.diagnosticos.insertar(**campos)
