"""Repositorio de solicitudes de reposición (sección 4.9.2)."""

from core.configuracion import ConfiguracionSistema

from .daos import ReposicionDAO
from .models import EstadoSolicitud


class ReposicionRepository:
    def __init__(self, dao=None):
        self.dao = dao or ReposicionDAO()

    def guardar(self, **campos):
        return self.dao.insertar(**campos)

    def actualizar(self, solicitud):
        self.dao.actualizar(solicitud)

    def buscar(self, codigo, con_bloqueo=False):
        return self.dao.buscar_por_codigo(codigo, con_bloqueo)

    def listar_pendientes(self):
        return self.dao.listar_por_estado([EstadoSolicitud.PENDIENTE])

    def autorizadas_para(self, centro_id):
        return self.dao.listar_por_estado([EstadoSolicitud.AUTORIZADA], centro_id)

    def de_orden(self, orden_id):
        return self.dao.listar_por_orden(orden_id)

    def todas(self):
        return self.dao.listar_todas()

    def siguiente_codigo(self):
        prefijo = ConfiguracionSistema().prefijo_solicitud
        ultimo = self.dao.ultimo_codigo()
        numero = int(ultimo.replace(prefijo, "")) + 1 if ultimo else 1
        return f"{prefijo}{numero:05d}"
