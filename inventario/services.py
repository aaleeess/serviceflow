"""Servicios de inventario: reserva atómica (RF-10, CU-08) y movimientos de stock (RF-09, RF-11)."""

from django.db import transaction

from core.configuracion import EstadoOrden
from core.excepciones import AccesoDenegado, ErrorNegocio, StockInsuficiente
from core.repositories import BitacoraRepository, PerfilRepository

from .dtos import (DisponibilidadCentroDTO, FilaReservaDTO, MovimientoDTO, OpcionesFaltanteDTO,
                   PanelReservasDTO, ResultadoReservaDTO, StockDTO)
from .models import TipoMovimiento
from .repositories import InventarioRepository, MovimientoRepository, ReservaRepository


def centro_de_empleado(usuario, perfiles=None):
    centro = (perfiles or PerfilRepository()).centro_de(usuario)
    if centro is None:
        raise ErrorNegocio("Tu cuenta no tiene un centro asignado. Pide al administrador que lo asigne.")
    return centro


class ReservaService:
    def __init__(self, inventario=None, reservas=None, bitacora=None, fuente=None):
        self.inventario = inventario or InventarioRepository()
        self.reservas = reservas or ReservaRepository()
        self.bitacora = bitacora or BitacoraRepository()
        # Cualquier FuenteInventario sirve: la base del piloto o un InventarioExternoAdapter.
        self.fuente = fuente or self.inventario

    def disponibilidad(self, repuesto_id):
        return self.fuente.disponibilidad_por_centro(repuesto_id)

    @transaction.atomic
    def reservar(self, usuario, codigo_orden):
        """Transacción atómica de la sección 2.7.

        Bloquea la orden y el registro de inventario, comprueba RN-01 y
        "físico − reservado ≥ cantidad" (RN-02), registra la reserva y la bitácora.
        Si algo falla, la transacción se revierte y no queda nada a medias.
        """
        from ordenes.repositories import OrdenRepository
        from ordenes.services import OrdenService

        centro = centro_de_empleado(usuario)
        ordenes = OrdenRepository()
        orden = ordenes.buscar_por_codigo(codigo_orden, con_bloqueo=True)
        if orden is None or orden.centro_id != centro.id:
            raise AccesoDenegado("Esa orden no es de tu centro.")
        diag = getattr(orden, "diagnostico", None)
        if diag is None:  # RN-01
            raise ErrorNegocio("No se puede reservar: la orden todavía no tiene diagnóstico.")
        if diag.repuesto_id is None:
            raise ErrorNegocio("Esta reparación no necesita repuesto.")
        if orden.estado != EstadoOrden.EN_ESPERA_REPUESTO or self.reservas.buscar_por_orden(orden.id):
            raise ErrorNegocio("Esta orden ya tiene su repuesto reservado.")

        inv = self.inventario.obtener_con_bloqueo(diag.repuesto_id, orden.centro_id)
        disponible = inv.disponible if inv else 0
        if disponible < diag.cantidad:  # RN-02 y RN-03
            faltante = diag.cantidad - disponible
            raise StockInsuficiente(
                f"No hay stock suficiente: faltan {faltante} de {diag.cantidad}. "
                "Pide un traslado o una reposición.", faltante)

        inv.stock_reservado += diag.cantidad
        self.inventario.guardar(inv)
        self.reservas.guardar(orden=orden, inventario=inv, cantidad=diag.cantidad, registrada_por=usuario)
        self.bitacora.registrar(usuario, "RESERVAR_REPUESTO", orden.codigo,
                                f"{diag.repuesto} x{diag.cantidad} en {orden.centro}")
        OrdenService().cambiar_estado(orden, EstadoOrden.EN_REPARACION, usuario,
                                      "Tu repuesto ya está separado. Empezó la reparación",
                                      aviso="Llegó tu repuesto")
        return ResultadoReservaDTO(True, f"Repuesto reservado para {orden.codigo}. La orden pasó a En reparación.")


class InventarioService:
    def __init__(self, inventario=None, reservas=None, movimientos=None, bitacora=None):
        self.inventario = inventario or InventarioRepository()
        self.reservas = reservas or ReservaRepository()
        self.movimientos = movimientos or MovimientoRepository()
        self.bitacora = bitacora or BitacoraRepository()

    # ---------- Consultas (RF-09) ----------

    def stock_del_centro(self, usuario):
        centro = centro_de_empleado(usuario)
        filas = [StockDTO(i.id, i.repuesto.nombre, i.repuesto.codigo_pieza, i.stock_fisico, i.stock_reservado,
                          i.disponible) for i in self.inventario.del_centro(centro.id)]
        return centro, filas

    def movimientos_del_centro(self, usuario):
        centro = centro_de_empleado(usuario)
        return [MovimientoDTO(m.fecha, m.get_tipo_display(), m.inventario.repuesto.nombre, m.cantidad, m.motivo,
                              m.referencia, m.usuario.get_full_name() or m.usuario.username)
                for m in self.movimientos.del_centro(centro.id)]

    def panel_reservas(self, usuario, filtro="todas", busqueda="", codigo=None):
        from coordinacion.repositories import ReposicionRepository
        from coordinacion.models import EstadoSolicitud
        from ordenes.repositories import OrdenRepository

        centro = centro_de_empleado(usuario)
        ordenes = OrdenRepository().listar(centro.id, [EstadoOrden.RECIBIDA, EstadoOrden.EN_EVALUACION,
                                                       EstadoOrden.EN_ESPERA_REPUESTO, EstadoOrden.EN_REPARACION])
        solicitudes = ReposicionRepository()
        filas = []
        for o in ordenes:
            diag = getattr(o, "diagnostico", None)
            if o.estado in (EstadoOrden.RECIBIDA, EstadoOrden.EN_EVALUACION):
                # RN-01 y Figura 2: se muestra con el botón Reservar desactivado.
                filas.append(FilaReservaDTO(o.codigo, o.modelo_equipo, o.actualizada, None, "Por definir",
                                            "El técnico aún no diagnostica", 0, 0, "sin_diagnostico", 0))
                continue
            if diag is None or diag.repuesto is None:
                continue
            inv = self.inventario.obtener(diag.repuesto_id, centro.id)
            disponible = inv.disponible if inv else 0
            if o.estado == EstadoOrden.EN_REPARACION:
                if not self.reservas.buscar_por_orden(o.id):
                    continue
                situacion, faltante = "reservada", 0
            else:
                faltante = max(diag.cantidad - disponible, 0)
                situacion = "lista" if faltante == 0 else "falta"
                en_curso = [s for s in solicitudes.de_orden(o.id)
                            if s.estado in (EstadoSolicitud.PENDIENTE, EstadoSolicitud.AUTORIZADA)]
                if faltante and en_curso:
                    situacion = "autorizada" if en_curso[0].estado == EstadoSolicitud.AUTORIZADA else "solicitada"
            filas.append(FilaReservaDTO(o.codigo, o.modelo_equipo, o.actualizada, o.fecha_estimada,
                                        diag.repuesto.nombre, diag.repuesto.codigo_pieza, diag.cantidad,
                                        disponible, situacion, faltante))

        por_reservar = [f for f in filas if f.situacion not in ("reservada", "sin_diagnostico")]
        agotados = [i.repuesto.nombre for i in self.inventario.del_centro(centro.id) if i.disponible == 0]
        resumen = {
            "por_reservar": len(por_reservar),
            "por_reservar_codigos": [f.orden for f in por_reservar],
            "falta": len([f for f in filas if f.faltante]),
            "agotados": len(agotados),
            "reservadas": [f for f in filas if f.situacion == "reservada"],
        }
        visibles = filas
        if filtro == "falta":
            visibles = [f for f in visibles if f.faltante]
        if busqueda:
            b = busqueda.lower()
            visibles = [f for f in visibles if b in f.orden.lower() or b in f.repuesto.lower()
                        or b in f.codigo_pieza.lower() or b in f.modelo_equipo.lower()]
        panel = PanelReservasDTO(visibles, resumen, filtro, busqueda, agotados=agotados)

        objetivo = next((f for f in filas if f.orden == codigo), None) if codigo else None
        if objetivo is None:
            objetivo = next((f for f in filas if f.situacion == "falta"), None)
        if objetivo is not None and objetivo.faltante:
            panel.opciones = self.opciones_faltante(centro, objetivo, solicitudes)
        return centro, panel

    def opciones_faltante(self, centro, fila, solicitudes):
        from ordenes.repositories import OrdenRepository

        orden = OrdenRepository().buscar_por_codigo(fila.orden)
        diag = orden.diagnostico
        por_centro = []
        for nombre, centro_id, disponible in ReservaService(self.inventario).disponibilidad(diag.repuesto_id):
            es_este = centro_id == centro.id
            por_centro.append(DisponibilidadCentroDTO(centro_id, nombre, disponible, es_este,
                                                      not es_este and disponible >= fila.faltante))
        por_centro.sort(key=lambda c: not c.es_este)
        texto = ""
        if fila.situacion == "solicitada":
            texto = "Ya pediste el repuesto. Falta que el coordinador lo apruebe."
        elif fila.situacion == "autorizada":
            texto = "El coordinador aprobó la solicitud. Regístrala en Registrar ingreso."
        return OpcionesFaltanteDTO(fila.orden, diag.repuesto.nombre, fila.faltante, por_centro, texto)

    # ---------- Movimientos (RF-11) ----------

    def consumir_reservas(self, orden, usuario):
        """Al terminar la reparación, la pieza reservada sale del stock físico."""
        for reserva in self.reservas.buscar_por_orden(orden.id):
            if reserva.consumida:
                continue
            inv = self.inventario.obtener_con_bloqueo(reserva.inventario.repuesto_id, reserva.inventario.centro_id)
            inv.stock_fisico -= reserva.cantidad
            inv.stock_reservado -= reserva.cantidad
            self.inventario.guardar(inv)
            self.reservas.marcar_consumida(reserva)
            self.movimientos.registrar(inv, TipoMovimiento.CONSUMO, -reserva.cantidad, usuario,
                                       "Usado en la reparación", orden.codigo)
            self.bitacora.registrar(usuario, "CONSUMIR_REPUESTO", orden.codigo, f"{inv.repuesto} x{reserva.cantidad}")

    @transaction.atomic
    def ajustar(self, usuario, inventario_id, nueva_cantidad, motivo):
        centro = centro_de_empleado(usuario)
        motivo = (motivo or "").strip()
        if not motivo:
            raise ErrorNegocio("Escribe el motivo del ajuste.")
        try:
            nueva_cantidad = int(nueva_cantidad)
        except (TypeError, ValueError):
            raise ErrorNegocio("Escribe la nueva cantidad en números.")
        inv = next((i for i in self.inventario.del_centro(centro.id) if i.id == int(inventario_id)), None)
        if inv is None:
            raise AccesoDenegado("Ese repuesto no es de tu centro.")
        inv = self.inventario.obtener_con_bloqueo(inv.repuesto_id, centro.id)
        if nueva_cantidad < inv.stock_reservado:  # RNF-06
            raise ErrorNegocio(f"No puede quedar menos de {inv.stock_reservado}: esas unidades ya están reservadas.")
        diferencia = nueva_cantidad - inv.stock_fisico
        if diferencia == 0:
            raise ErrorNegocio("La cantidad es la misma que ya está registrada.")
        inv.stock_fisico = nueva_cantidad
        self.inventario.guardar(inv)
        self.movimientos.registrar(inv, TipoMovimiento.AJUSTE, diferencia, usuario, motivo)
        self.bitacora.registrar(usuario, "AJUSTAR_STOCK", inv.repuesto.codigo_pieza,
                                f"{inv.repuesto} en {centro}: {diferencia:+d}. {motivo}")

    def ingresar(self, usuario, repuesto_id, centro_id, cantidad, tipo, referencia, motivo):
        inv = self.inventario.obtener_con_bloqueo(repuesto_id, centro_id, crear=True)
        inv.stock_fisico += cantidad
        self.inventario.guardar(inv)
        self.movimientos.registrar(inv, tipo, cantidad, usuario, motivo, referencia)
        return inv

    def retirar(self, usuario, repuesto_id, centro_id, cantidad, referencia, motivo):
        inv = self.inventario.obtener_con_bloqueo(repuesto_id, centro_id)
        if inv is None or inv.disponible < cantidad:
            raise StockInsuficiente("El centro de origen ya no tiene unidades disponibles para el traslado.")
        inv.stock_fisico -= cantidad
        self.inventario.guardar(inv)
        self.movimientos.registrar(inv, TipoMovimiento.TRASLADO_SALIDA, -cantidad, usuario, motivo, referencia)
        return inv
