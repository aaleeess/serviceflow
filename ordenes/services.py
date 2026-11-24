"""Servicio de órdenes: reglas del ciclo de una reparación (RF-02, RF-04, RF-05, RF-07, RF-08, RF-14)."""

from django.db import transaction
from django.utils import timezone

from core.avisos import AvisoService
from core.configuracion import ConfiguracionSistema, EstadoOrden
from core.excepciones import AccesoDenegado, ErrorNegocio
from core.repositories import BitacoraRepository, PerfilRepository
from inventario.repositories import CatalogoRepository, InventarioRepository

from .dtos import (BandejaTecnicoDTO, EventoDTO, OpcionRepuestoDTO, OrdenTecnicoDTO, PasoDTO,
                   SeguimientoDTO, SolicitudDTO)
from .repositories import OrdenRepository


def nombre_de(usuario):
    return usuario.get_full_name() or usuario.username


class OrdenService:
    FILTROS_TECNICO = {
        "todas": None,
        "diagnosticar": [EstadoOrden.RECIBIDA, EstadoOrden.EN_EVALUACION],
        "espera": [EstadoOrden.EN_ESPERA_REPUESTO],
        "reparacion": [EstadoOrden.EN_REPARACION, EstadoOrden.REPARADA],
    }

    def __init__(self, ordenes=None, bitacora=None, avisos=None, catalogo=None, inventario=None, perfiles=None):
        self.ordenes = ordenes or OrdenRepository()
        self.bitacora = bitacora or BitacoraRepository()
        self.avisos = avisos or AvisoService()
        self.catalogo = catalogo or CatalogoRepository()
        self.inventario = inventario or InventarioRepository()
        self.perfiles = perfiles or PerfilRepository()
        self.config = ConfiguracionSistema()

    # ---------- Cambio de estado: un solo lugar para validar, registrar y avisar ----------

    def cambiar_estado(self, orden, nuevo, usuario, descripcion, motivo="", operacion="CAMBIAR_ESTADO",
                       aviso=None):
        anterior = orden.estado
        if not self.config.transicion_valida(anterior, nuevo):
            raise ErrorNegocio(f"La orden {orden.codigo} no puede pasar de "
                               f"{EstadoOrden.ETIQUETAS[anterior]} a {EstadoOrden.ETIQUETAS[nuevo]}.")
        orden.estado = nuevo
        self.ordenes.actualizar(orden, "estado")
        self.ordenes.registrar_historial(orden, anterior, nuevo, descripcion, usuario, motivo)
        self.bitacora.registrar(usuario, operacion, orden.codigo,
                                f"{EstadoOrden.ETIQUETAS[anterior]} → {EstadoOrden.ETIQUETAS[nuevo]}"
                                + (f". Motivo: {motivo}" if motivo else ""))
        if aviso:
            self.avisos.notificar(orden, aviso, f"{descripcion}\n\nConsulta el detalle en Mis reparaciones.")

    # ---------- Cliente ----------

    @transaction.atomic
    def registrar_solicitud(self, cliente, modelo_equipo, falla_reportada, centro_id):
        """CU-02 / RF-04: valida, crea la orden con código único y la deja Recibida."""
        modelo_equipo, falla_reportada = (modelo_equipo or "").strip(), (falla_reportada or "").strip()
        if not modelo_equipo or not falla_reportada or not centro_id:
            raise ErrorNegocio("Completa el modelo, la falla y el centro.")
        centro = self.catalogo.centro(centro_id)
        if centro is None:
            raise ErrorNegocio("Elige un centro del piloto.")
        orden = self.ordenes.guardar_nueva(codigo=self.ordenes.siguiente_codigo(), cliente=cliente,
                                           centro=centro, modelo_equipo=modelo_equipo,
                                           falla_reportada=falla_reportada)
        self.ordenes.registrar_historial(orden, "", EstadoOrden.RECIBIDA, "Solicitud registrada", cliente)
        self.bitacora.registrar(cliente, "REGISTRAR_SOLICITUD", orden.codigo, f"{modelo_equipo} en {centro}")
        self.avisos.notificar(orden, "Recibimos tu solicitud",
                              f"Registramos tu {modelo_equipo} en {centro}. Tu código es {orden.codigo}.")
        return SolicitudDTO(codigo=orden.codigo, estado_texto=self.config.estado_cliente[orden.estado])

    def _seguimiento(self, orden):
        paso_actual = self.config.paso_por_estado[orden.estado]
        cancelada = orden.estado == EstadoOrden.CANCELADA
        pasos = []
        for i, nombre in enumerate(self.config.pasos_cliente):
            if cancelada:
                situacion = "pendiente"
            elif i < paso_actual or orden.estado == EstadoOrden.ENTREGADA:
                situacion = "hecho"
            elif i == paso_actual:
                situacion = "actual"
            else:
                situacion = "pendiente"
            pasos.append(PasoDTO(nombre, situacion))
        historial = [EventoDTO(h.descripcion, h.fecha) for h in reversed(self.ordenes.historial_de(orden))]
        diag = getattr(orden, "diagnostico", None)
        pieza = ""
        if diag and diag.repuesto:
            pieza = f"{diag.repuesto.nombre}" + (f" ({diag.cantidad} unidades)" if diag.cantidad > 1 else "")
        return SeguimientoDTO(
            codigo=orden.codigo, modelo_equipo=orden.modelo_equipo, falla_reportada=orden.falla_reportada,
            centro=orden.centro.nombre, diagnostico=diag.descripcion if diag else "",
            pieza=pieza if diag else "", estado=orden.estado, estado_texto=self.config.estado_cliente[orden.estado],
            pasos=pasos, fecha_estimada=orden.fecha_estimada, historial=historial,
            puede_cancelar=orden.estado == EstadoOrden.RECIBIDA,
            esperando_repuesto=orden.estado == EstadoOrden.EN_ESPERA_REPUESTO, cancelada=cancelada,
        )

    def mis_reparaciones(self, cliente):
        return [self._seguimiento(o) for o in self.ordenes.buscar_por_cliente(cliente.id)]

    def seguimiento(self, cliente, codigo):
        """CU-04: valida la propiedad. Si no es suya, no revela si la orden existe."""
        orden = self.ordenes.buscar_por_codigo(codigo)
        if orden is None or orden.cliente_id != cliente.id:
            raise AccesoDenegado("No encontramos esa reparación en tu cuenta.")
        return self._seguimiento(orden)

    @transaction.atomic
    def cancelar_por_cliente(self, cliente, codigo, motivo=""):
        orden = self.ordenes.buscar_por_codigo(codigo, con_bloqueo=True)
        if orden is None or orden.cliente_id != cliente.id:
            raise AccesoDenegado("No encontramos esa reparación en tu cuenta.")
        if orden.estado != EstadoOrden.RECIBIDA:
            raise ErrorNegocio("Solo puedes cancelar mientras tu solicitud está en Recibida.")
        self.cambiar_estado(orden, EstadoOrden.CANCELADA, cliente, "Cancelaste la solicitud",
                            motivo.strip() or "Cancelada por el cliente", "CANCELAR_ORDEN")

    # ---------- Técnico ----------

    def _centro_empleado(self, usuario):
        centro = self.perfiles.centro_de(usuario)
        if centro is None:
            raise ErrorNegocio("Tu cuenta no tiene un centro asignado. Pide al administrador que lo asigne.")
        return centro

    def _orden_del_centro(self, usuario, codigo, con_bloqueo=False):
        centro = self._centro_empleado(usuario)
        orden = self.ordenes.buscar_por_codigo(codigo, con_bloqueo)
        if orden is None or orden.centro_id != centro.id:
            raise AccesoDenegado("Esa orden no es de tu centro.")
        return orden

    def _siguiente_paso(self, orden):
        e = orden.estado
        if e in (EstadoOrden.RECIBIDA, EstadoOrden.EN_EVALUACION):
            return "diagnosticar"
        if e == EstadoOrden.EN_ESPERA_REPUESTO:
            return "almacen"
        if e == EstadoOrden.EN_REPARACION:
            return "marcar_reparada" if orden.fecha_estimada else "confirmar_fecha"
        if e == EstadoOrden.REPARADA:
            return "entregar"
        return "ninguno"

    def _dto_tecnico(self, orden):
        diag = getattr(orden, "diagnostico", None)
        return OrdenTecnicoDTO(
            codigo=orden.codigo, modelo_equipo=orden.modelo_equipo, falla_reportada=orden.falla_reportada,
            cliente=nombre_de(orden.cliente), estado=orden.estado,
            estado_texto=EstadoOrden.ETIQUETAS[orden.estado], fecha_estimada=orden.fecha_estimada,
            siguiente=self._siguiente_paso(orden),
            repuesto=diag.repuesto.nombre if diag and diag.repuesto else "",
            diagnostico=diag.descripcion if diag else "",
        )

    def bandeja_tecnico(self, tecnico, filtro="todas", codigo=None):
        centro = self._centro_empleado(tecnico)
        visibles = [o for o in self.ordenes.listar(centro.id) if o.estado in EstadoOrden.ABIERTOS]
        conteos = {k: len([o for o in visibles if v is None or o.estado in v])
                   for k, v in self.FILTROS_TECNICO.items()}
        estados = self.FILTROS_TECNICO.get(filtro, None)
        lista = [self._dto_tecnico(o) for o in visibles if estados is None or o.estado in estados]
        bandeja = BandejaTecnicoDTO(ordenes=lista, conteos=conteos,
                                    filtro=filtro if filtro in self.FILTROS_TECNICO else "todas")
        elegida = next((o for o in visibles if o.codigo == codigo), None) if codigo else None
        if elegida is None:
            elegida = next((o for o in visibles if self._siguiente_paso(o) == "diagnosticar"), None)
        if elegida is not None:
            bandeja.seleccionada = self._dto_tecnico(elegida)
            if bandeja.seleccionada.siguiente == "diagnosticar":
                bandeja.repuestos = self.repuestos_compatibles(elegida)
        return bandeja

    def repuestos_compatibles(self, orden):
        """RF-08: solo se ofrecen repuestos del mismo modelo del equipo."""
        opciones = []
        for r in self.catalogo.listar_repuestos():
            if r.es_compatible(orden.modelo_equipo):
                inv = self.inventario.obtener(r.id, orden.centro_id)
                opciones.append(OpcionRepuestoDTO(r.id, r.nombre, inv.disponible if inv else 0))
        return opciones

    @transaction.atomic
    def diagnosticar(self, tecnico, codigo, descripcion, repuesto_id=None, cantidad=1):
        """RF-07 / RF-08. Con repuesto la orden espera a almacén; sin repuesto pasa a reparación."""
        orden = self._orden_del_centro(tecnico, codigo, con_bloqueo=True)
        if orden.estado not in (EstadoOrden.RECIBIDA, EstadoOrden.EN_EVALUACION):
            raise ErrorNegocio("Esta orden ya tiene diagnóstico.")
        descripcion = (descripcion or "").strip()
        if not descripcion:
            raise ErrorNegocio("Escribe qué encontraste: el diagnóstico es obligatorio.")
        repuesto = None
        if repuesto_id:
            repuesto = self.catalogo.repuesto(repuesto_id)
            if repuesto is None or not repuesto.es_compatible(orden.modelo_equipo):
                raise ErrorNegocio(f"Ese repuesto no es compatible con {orden.modelo_equipo}.")
            if not cantidad or int(cantidad) < 1:
                raise ErrorNegocio("La cantidad debe ser al menos 1.")
        if orden.estado == EstadoOrden.RECIBIDA:
            self.cambiar_estado(orden, EstadoOrden.EN_EVALUACION, tecnico, "El técnico inició la evaluación")
        self.ordenes.guardar_diagnostico(orden=orden, tecnico=tecnico, descripcion=descripcion,
                                         repuesto=repuesto, cantidad=int(cantidad) if repuesto else 1)
        self.bitacora.registrar(tecnico, "REGISTRAR_DIAGNOSTICO", orden.codigo,
                                f"{descripcion}" + (f" · {repuesto} x{cantidad}" if repuesto else " · sin repuesto"))
        if repuesto:
            self.cambiar_estado(orden, EstadoOrden.EN_ESPERA_REPUESTO, tecnico, f"Diagnóstico: {descripcion}",
                                aviso="Tu equipo ya tiene diagnóstico")
        else:
            self.cambiar_estado(orden, EstadoOrden.EN_REPARACION, tecnico, f"Diagnóstico: {descripcion}",
                                aviso="Tu equipo entró a reparación")

    @transaction.atomic
    def confirmar_fecha(self, tecnico, codigo, fecha):
        """RF-14: la fecha solo se muestra al cliente cuando el técnico la confirma."""
        orden = self._orden_del_centro(tecnico, codigo, con_bloqueo=True)
        if orden.estado != EstadoOrden.EN_REPARACION:
            raise ErrorNegocio("Solo se confirma la fecha cuando la orden está En reparación.")
        if fecha is None:
            raise ErrorNegocio("Elige la fecha de entrega.")
        if fecha < timezone.localdate():
            raise ErrorNegocio("La fecha de entrega no puede ser anterior a hoy.")
        orden.fecha_estimada = fecha
        self.ordenes.actualizar(orden, "fecha_estimada")
        texto = f"Fecha de entrega confirmada: {fecha:%d/%m/%Y}"
        self.ordenes.registrar_historial(orden, orden.estado, orden.estado, texto, tecnico)
        self.bitacora.registrar(tecnico, "CONFIRMAR_FECHA", orden.codigo, texto)
        self.avisos.notificar(orden, "Ya tienes fecha de entrega", texto)

    @transaction.atomic
    def marcar_reparada(self, tecnico, codigo):
        orden = self._orden_del_centro(tecnico, codigo, con_bloqueo=True)
        if orden.estado == EstadoOrden.EN_REPARACION and not orden.fecha_estimada:
            raise ErrorNegocio("Confirma primero la fecha de entrega.")
        from inventario.services import InventarioService  # evita importación circular

        InventarioService().consumir_reservas(orden, tecnico)
        self.cambiar_estado(orden, EstadoOrden.REPARADA, tecnico, "Reparación terminada. Ya puedes recogerlo",
                            operacion="MARCAR_REPARADA", aviso="Tu equipo está listo")

    @transaction.atomic
    def registrar_entrega(self, tecnico, codigo):
        orden = self._orden_del_centro(tecnico, codigo, con_bloqueo=True)
        self.cambiar_estado(orden, EstadoOrden.ENTREGADA, tecnico, "Equipo entregado", operacion="REGISTRAR_ENTREGA",
                            aviso="Entregamos tu equipo")

    # ---------- Coordinador ----------

    def cancelables(self):
        return [self._dto_tecnico(o) for o in self.ordenes.listar(estados=[EstadoOrden.RECIBIDA,
                                                                         EstadoOrden.EN_EVALUACION])]

    @transaction.atomic
    def cancelar_por_coordinador(self, coordinador, codigo, motivo):
        orden = self.ordenes.buscar_por_codigo(codigo, con_bloqueo=True)
        if orden is None:
            raise ErrorNegocio("No existe esa orden.")
        if orden.estado not in (EstadoOrden.RECIBIDA, EstadoOrden.EN_EVALUACION):
            raise ErrorNegocio("Solo se cancelan órdenes Recibidas o En evaluación.")
        if not (motivo or "").strip():
            raise ErrorNegocio("Escribe el motivo de la cancelación.")
        self.cambiar_estado(orden, EstadoOrden.CANCELADA, coordinador, "El centro canceló la solicitud",
                            motivo.strip(), "CANCELAR_ORDEN", aviso="Tu solicitud fue cancelada")
