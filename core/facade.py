"""Patrón estructural Facade (sección 4.3).

ServicioPosventaFacade ofrece operaciones sencillas a las vistas. Las vistas nunca llaman a
repositorios ni a la base de datos: Vista → Facade → Service → Repository → DAO (sección 4.9).
"""

from coordinacion.services import ReporteService, ReposicionService
from core.avisos import AvisoService
from inventario.repositories import CatalogoRepository
from inventario.services import InventarioService, ReservaService
from ordenes.services import OrdenService


class ServicioPosventaFacade:
    def __init__(self):
        self.ordenes = OrdenService()
        self.reservas = ReservaService()
        self.inventario = InventarioService()
        self.reposiciones = ReposicionService()
        self.reportes = ReporteService()
        self.catalogo = CatalogoRepository()
        self.avisos_servicio = AvisoService()

    # Cliente
    def centros(self):
        return self.catalogo.listar_centros()

    def registrar_solicitud(self, cliente, modelo, falla, centro_id):
        return self.ordenes.registrar_solicitud(cliente, modelo, falla, centro_id)

    def mis_reparaciones(self, cliente):
        return self.ordenes.mis_reparaciones(cliente)

    def seguimiento(self, cliente, codigo):
        return self.ordenes.seguimiento(cliente, codigo)

    def cancelar_solicitud(self, cliente, codigo, motivo=""):
        return self.ordenes.cancelar_por_cliente(cliente, codigo, motivo)

    def avisos(self, cliente, marcar_leidos=False):
        """RF-06: avisos del cliente; al abrir la pantalla de avisos quedan como leídos."""
        return self.avisos_servicio.avisos_de(cliente, marcar_leidos=marcar_leidos)

    def avisos_de_orden(self, cliente, codigo):
        self.ordenes.seguimiento(cliente, codigo)  # valida que la orden sea suya (RN-06)
        return self.avisos_servicio.avisos_de(cliente, referencia=codigo)

    def avisos_nuevos(self, cliente):
        return self.avisos_servicio.cuantos_nuevos(cliente)

    # Técnico
    def bandeja_tecnico(self, tecnico, filtro, codigo=None):
        return self.ordenes.bandeja_tecnico(tecnico, filtro, codigo)

    def diagnosticar(self, tecnico, codigo, descripcion, repuesto_id, cantidad):
        return self.ordenes.diagnosticar(tecnico, codigo, descripcion, repuesto_id, cantidad)

    def confirmar_fecha(self, tecnico, codigo, fecha):
        return self.ordenes.confirmar_fecha(tecnico, codigo, fecha)

    def marcar_reparada(self, tecnico, codigo):
        return self.ordenes.marcar_reparada(tecnico, codigo)

    def registrar_entrega(self, tecnico, codigo):
        return self.ordenes.registrar_entrega(tecnico, codigo)

    # Almacén (y técnico para consultar stock)
    def stock_del_centro(self, usuario):
        return self.inventario.stock_del_centro(usuario)

    def panel_reservas(self, almacenero, filtro, busqueda, codigo=None):
        return self.inventario.panel_reservas(almacenero, filtro, busqueda, codigo)

    def reservar(self, almacenero, codigo):
        return self.reservas.reservar(almacenero, codigo)

    def solicitar(self, almacenero, codigo, tipo, centro_origen_id=None):
        return self.reposiciones.crear(almacenero, codigo, tipo, centro_origen_id)

    def autorizadas(self, almacenero):
        return self.reposiciones.autorizadas_del_centro(almacenero)

    def ejecutar_solicitud(self, almacenero, codigo):
        return self.reposiciones.ejecutar(almacenero, codigo)

    def ajustar_stock(self, almacenero, inventario_id, cantidad, motivo):
        return self.inventario.ajustar(almacenero, inventario_id, cantidad, motivo)

    def movimientos(self, almacenero):
        return self.inventario.movimientos_del_centro(almacenero)

    # Coordinador
    def solicitudes_pendientes(self, tipo="", centro=""):
        return self.reposiciones.pendientes(tipo, centro)

    def resolver_solicitud(self, coordinador, codigo, aprobar, motivo=""):
        return self.reposiciones.resolver(coordinador, codigo, aprobar, motivo)

    def reportes_generales(self):
        return self.reportes.generar()

    def ordenes_cancelables(self):
        return self.ordenes.cancelables()

    def cancelar_orden(self, coordinador, codigo, motivo):
        return self.ordenes.cancelar_por_coordinador(coordinador, codigo, motivo)
