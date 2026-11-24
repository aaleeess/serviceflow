"""DAO del módulo core: operaciones básicas sobre una tabla cada uno (sección 4.9.3)."""

from .models import Aviso, Bitacora, PerfilEmpleado


class BitacoraDAO:
    def insertar(self, **campos):
        return Bitacora.objects.create(**campos)

    def listar(self, limite=50):
        return list(Bitacora.objects.select_related("usuario")[:limite])


class AvisoDAO:
    def insertar(self, **campos):
        return Aviso.objects.create(**campos)

    def listar_por_cliente(self, cliente_id, referencia=None):
        qs = Aviso.objects.filter(cliente_id=cliente_id)
        if referencia:
            qs = qs.filter(referencia=referencia)
        return list(qs)

    def contar_no_leidos(self, cliente_id):
        return Aviso.objects.filter(cliente_id=cliente_id, leido=False).count()

    def marcar_leidos(self, cliente_id, ids):
        Aviso.objects.filter(cliente_id=cliente_id, id__in=ids).update(leido=True)


class PerfilDAO:
    def buscar_por_usuario(self, usuario_id):
        return PerfilEmpleado.objects.select_related("centro").filter(usuario_id=usuario_id).first()
