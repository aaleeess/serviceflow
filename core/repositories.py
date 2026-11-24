"""Repositorios del módulo core (sección 4.9.2). Solo los servicios los usan."""

from .daos import AvisoDAO, BitacoraDAO, PerfilDAO


class BitacoraRepository:
    """RN-05: cada cambio guarda usuario, fecha, operación y referencia."""

    def __init__(self, dao=None):
        self.dao = dao or BitacoraDAO()

    def registrar(self, usuario, operacion, referencia, detalle=""):
        return self.dao.insertar(usuario=usuario, operacion=operacion, referencia=referencia, detalle=detalle)


class AvisoRepository:
    def __init__(self, dao=None):
        self.dao = dao or AvisoDAO()

    def guardar(self, cliente, referencia, asunto, mensaje):
        return self.dao.insertar(cliente=cliente, referencia=referencia, asunto=asunto, mensaje=mensaje)

    def de_cliente(self, cliente_id, referencia=None):
        """RN-06: solo los avisos del propio cliente."""
        return self.dao.listar_por_cliente(cliente_id, referencia)

    def no_leidos(self, cliente_id):
        return self.dao.contar_no_leidos(cliente_id)

    def marcar_leidos(self, cliente_id, avisos):
        self.dao.marcar_leidos(cliente_id, [a.id for a in avisos if not a.leido])


class PerfilRepository:
    def __init__(self, dao=None):
        self.dao = dao or PerfilDAO()

    def centro_de(self, usuario):
        perfil = self.dao.buscar_por_usuario(usuario.id)
        return perfil.centro if perfil else None
