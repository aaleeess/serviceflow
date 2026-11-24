"""Reposición y traslados (RF-12, RF-13, CU-10, CU-11, RN-03, RN-04) y reportes (RF-15)."""

from collections import Counter

from django.db import transaction
from django.utils import timezone

from core.configuracion import EstadoOrden
from core.excepciones import AccesoDenegado, ErrorNegocio
from core.repositories import BitacoraRepository
from inventario.models import TipoMovimiento
from inventario.repositories import CatalogoRepository, InventarioRepository
from inventario.services import InventarioService, centro_de_empleado
from ordenes.repositories import OrdenRepository

from .dtos import SolicitudAutorizadaDTO, SolicitudPendienteDTO
from .models import EstadoSolicitud, TipoSolicitud
from .repositories import ReposicionRepository


def nombre_de(usuario):
    return (usuario.get_full_name() or usuario.username) if usuario else ""


class ReposicionService:
    def __init__(self, solicitudes=None, ordenes=None, inventario=None, catalogo=None, bitacora=None):
        self.solicitudes = solicitudes or ReposicionRepository()
        self.ordenes = ordenes or OrdenRepository()
        self.inventario = inventario or InventarioRepository()
        self.catalogo = catalogo or CatalogoRepository()
        self.bitacora = bitacora or BitacoraRepository()

    @transaction.atomic
    def crear(self, almacenero, codigo_orden, tipo, centro_origen_id=None):
        """CU-10: almacén pide el faltante. Queda Pendiente de autorización (RN-03: sin fecha definitiva)."""
        centro = centro_de_empleado(almacenero)
        orden = self.ordenes.buscar_por_codigo(codigo_orden, con_bloqueo=True)
        if orden is None or orden.centro_id != centro.id:
            raise AccesoDenegado("Esa orden no es de tu centro.")
        diag = getattr(orden, "diagnostico", None)
        if orden.estado != EstadoOrden.EN_ESPERA_REPUESTO or diag is None or diag.repuesto_id is None:
            raise ErrorNegocio("Esa orden no está esperando un repuesto.")
        en_curso = [s for s in self.solicitudes.de_orden(orden.id)
                    if s.estado in (EstadoSolicitud.PENDIENTE, EstadoSolicitud.AUTORIZADA)]
        if en_curso:
            raise ErrorNegocio(f"Ya hay una solicitud en curso para {orden.codigo} ({en_curso[0].codigo}).")
        inv = self.inventario.obtener(diag.repuesto_id, centro.id)
        faltante = diag.cantidad - (inv.disponible if inv else 0)
        if faltante <= 0:
            raise ErrorNegocio("Ya hay stock suficiente: reserva el repuesto directamente.")

        origen = None
        if tipo == TipoSolicitud.TRASLADO:
            origen = self.catalogo.centro(centro_origen_id) if centro_origen_id else None
            if origen is None or origen.id == centro.id:
                raise ErrorNegocio("Elige el centro desde donde se traslada.")
            inv_origen = self.inventario.obtener(diag.repuesto_id, origen.id)
            if inv_origen is None or inv_origen.disponible < faltante:
                raise ErrorNegocio(f"{origen} no tiene {faltante} unidades disponibles.")
        elif tipo != TipoSolicitud.REPOSICION:
            raise ErrorNegocio("Tipo de solicitud no válido.")

        solicitud = self.solicitudes.guardar(codigo=self.solicitudes.siguiente_codigo(), orden=orden, tipo=tipo,
                                             repuesto=diag.repuesto, centro=centro, centro_origen=origen,
                                             cantidad=faltante, solicitante=almacenero)
        self.bitacora.registrar(almacenero, "SOLICITAR_" + tipo, solicitud.codigo,
                                f"{diag.repuesto} x{faltante} para {orden.codigo}"
                                + (f" desde {origen}" if origen else ""))
        return solicitud.codigo

    def _dto_pendiente(self, s):
        destino = self.inventario.obtener(s.repuesto_id, s.centro_id)
        origen = self.inventario.obtener(s.repuesto_id, s.centro_origen_id) if s.centro_origen_id else None
        necesita = s.orden.diagnostico.cantidad if s.orden and hasattr(s.orden, "diagnostico") else s.cantidad
        return SolicitudPendienteDTO(
            codigo=s.codigo, tipo=s.tipo, tipo_texto=s.get_tipo_display(), solicitante=nombre_de(s.solicitante),
            creada=s.creada, cantidad=s.cantidad, repuesto=s.repuesto.nombre, codigo_pieza=s.repuesto.codigo_pieza,
            orden=s.orden.codigo if s.orden else "", necesita=necesita, destino=s.centro.nombre,
            destino_disponible=destino.disponible if destino else 0,
            origen=s.centro_origen.nombre if s.centro_origen else "",
            origen_disponible=origen.disponible if origen else 0,
            origen_queda=(origen.disponible - s.cantidad) if origen else 0,
        )

    def pendientes(self, tipo="", centro=""):
        """Filtros rápidos del coordinador (Figura 3): por tipo y por centro que recibe."""
        todas = [self._dto_pendiente(s) for s in self.solicitudes.listar_pendientes()]
        visibles = [s for s in todas if (not tipo or s.tipo == tipo) and (not centro or s.destino == centro)]
        conteos = {
            "todas": len(todas),
            TipoSolicitud.TRASLADO: len([s for s in todas if s.tipo == TipoSolicitud.TRASLADO]),
            TipoSolicitud.REPOSICION: len([s for s in todas if s.tipo == TipoSolicitud.REPOSICION]),
            "centros": [(c.nombre, len([s for s in todas if s.destino == c.nombre]))
                        for c in self.catalogo.listar_centros()],
        }
        return visibles, conteos

    @transaction.atomic
    def resolver(self, coordinador, codigo, aprobar, motivo=""):
        """CU-11 / RN-04: solo el coordinador autoriza; para rechazar, el motivo es obligatorio."""
        s = self.solicitudes.buscar(codigo, con_bloqueo=True)
        if s is None:
            raise ErrorNegocio("No existe esa solicitud.")
        if s.estado != EstadoSolicitud.PENDIENTE:
            # CU-11 flujo alternativo: no se permite una segunda decisión; se muestra su estado actual.
            actual = self.solicitudes.buscar(codigo)
            quien = f" por {nombre_de(actual.revisor)}" if actual.revisor else ""
            cuando = f" el {timezone.localtime(actual.resuelta):%d/%m %H:%M}" if actual.resuelta else ""
            raise ErrorNegocio(f"{codigo} ya fue resuelta: está {actual.get_estado_display()}{quien}{cuando}"
                               + (f". Motivo: {actual.motivo_decision}" if actual.motivo_decision else "."))
        motivo = (motivo or "").strip()
        if not aprobar and not motivo:
            raise ErrorNegocio("Escribe el motivo para rechazar la solicitud.")
        s.estado = EstadoSolicitud.AUTORIZADA if aprobar else EstadoSolicitud.RECHAZADA
        s.motivo_decision, s.revisor, s.resuelta = motivo, coordinador, timezone.now()
        self.solicitudes.actualizar(s)
        self.bitacora.registrar(coordinador, "APROBAR_SOLICITUD" if aprobar else "RECHAZAR_SOLICITUD", s.codigo,
                                motivo or "Aprobada")

    def autorizadas_del_centro(self, almacenero):
        centro = centro_de_empleado(almacenero)
        return [SolicitudAutorizadaDTO(s.codigo, s.tipo, s.get_tipo_display(), s.cantidad, s.repuesto.nombre,
                                       s.orden.codigo if s.orden else "",
                                       s.centro_origen.nombre if s.centro_origen else "", nombre_de(s.revisor),
                                       s.resuelta)
                for s in self.solicitudes.autorizadas_para(centro.id)]

    @transaction.atomic
    def ejecutar(self, almacenero, codigo):
        """Almacén ejecuta el movimiento ya autorizado (RN-04): el stock entra al centro."""
        centro = centro_de_empleado(almacenero)
        s = self.solicitudes.buscar(codigo, con_bloqueo=True)
        if s is None or s.centro_id != centro.id:
            raise AccesoDenegado("Esa solicitud no es de tu centro.")
        if s.estado != EstadoSolicitud.AUTORIZADA:
            raise ErrorNegocio("Solo se registran solicitudes aprobadas por el coordinador.")
        inventario = InventarioService()
        referencia = s.orden.codigo if s.orden else s.codigo
        if s.tipo == TipoSolicitud.TRASLADO:
            inventario.retirar(almacenero, s.repuesto_id, s.centro_origen_id, s.cantidad, s.codigo,
                               f"Traslado a {s.centro} para {referencia}")
            inventario.ingresar(almacenero, s.repuesto_id, s.centro_id, s.cantidad, TipoMovimiento.TRASLADO_ENTRADA,
                                s.codigo, f"Traslado desde {s.centro_origen} para {referencia}")
        else:
            inventario.ingresar(almacenero, s.repuesto_id, s.centro_id, s.cantidad, TipoMovimiento.INGRESO,
                                s.codigo, f"Reposición para {referencia}")
        s.estado = EstadoSolicitud.ATENDIDA
        self.solicitudes.actualizar(s)
        self.bitacora.registrar(almacenero, "REGISTRAR_" + s.tipo, s.codigo, f"{s.repuesto} x{s.cantidad} en {centro}")


class ReporteService:
    """RF-15: reportes de órdenes y faltantes para el coordinador (los dos centros)."""

    def __init__(self, ordenes=None, inventario=None, solicitudes=None, catalogo=None):
        self.ordenes = ordenes or OrdenRepository()
        self.inventario = inventario or InventarioRepository()
        self.solicitudes = solicitudes or ReposicionRepository()
        self.catalogo = catalogo or CatalogoRepository()

    def generar(self):
        ordenes = self.ordenes.listar()
        cuenta = Counter(o.estado for o in ordenes)
        mayor = max(cuenta.values(), default=1)
        por_estado = [{"estado": EstadoOrden.ETIQUETAS[e], "clave": e, "cantidad": cuenta[e],
                       "porcentaje": round(cuenta[e] * 100 / mayor) if mayor else 0}
                      for e in [EstadoOrden.RECIBIDA, EstadoOrden.EN_EVALUACION, EstadoOrden.EN_ESPERA_REPUESTO,
                                EstadoOrden.EN_REPARACION, EstadoOrden.REPARADA, EstadoOrden.ENTREGADA,
                                EstadoOrden.CANCELADA] if cuenta[e]]
        entregadas = [o for o in ordenes if o.estado == EstadoOrden.ENTREGADA]

        stock = {(i.repuesto_id, i.centro_id): i for i in self.inventario.todo()}
        faltantes = []
        for o in ordenes:
            diag = getattr(o, "diagnostico", None)
            if o.estado == EstadoOrden.EN_ESPERA_REPUESTO and diag and diag.repuesto:
                inv = stock.get((diag.repuesto_id, o.centro_id))
                falta = diag.cantidad - (inv.disponible if inv else 0)
                if falta > 0:
                    faltantes.append({"repuesto": diag.repuesto.nombre, "centro": o.centro.nombre,
                                      "orden": o.codigo, "falta": falta})
        centros = self.catalogo.listar_centros()
        agotados = []
        for r in self.catalogo.listar_repuestos():
            sin = [c for c in centros if (stock.get((r.id, c.id)) is None or stock[(r.id, c.id)].disponible == 0)]
            for c in sin:
                otros = [(x.nombre, stock[(r.id, x.id)].disponible) for x in centros
                         if x.id != c.id and stock.get((r.id, x.id)) and stock[(r.id, x.id)].disponible > 0]
                agotados.append({"repuesto": r.nombre, "centro": c.nombre, "otros": otros})

        por_centro = []
        for c in centros:
            del_centro = Counter(o.estado for o in ordenes if o.centro_id == c.id)
            por_centro.append({"centro": c.nombre,
                               "estados": [(EstadoOrden.ETIQUETAS[e], del_centro[e]) for e in EstadoOrden.ABIERTOS
                                           + [EstadoOrden.ENTREGADA, EstadoOrden.CANCELADA]],
                               "total": sum(del_centro.values())})
        solicitudes = Counter(s.get_estado_display() for s in self.solicitudes.todas())
        pendientes = self.solicitudes.listar_pendientes()
        return {
            "abiertas": len([o for o in ordenes if o.estado in EstadoOrden.ABIERTOS]),
            "espera": cuenta[EstadoOrden.EN_ESPERA_REPUESTO],
            "entregadas": entregadas,
            "por_estado": por_estado,
            "faltantes": faltantes,
            "agotados": agotados,
            "por_centro": por_centro,
            "solicitudes": sorted(solicitudes.items()),
            "pendientes": len(pendientes),
            "pendientes_traslado": len([p for p in pendientes if p.tipo == TipoSolicitud.TRASLADO]),
        }
