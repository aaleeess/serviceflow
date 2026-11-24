"""Pruebas de las reglas de negocio y flujos (RF, RN y CU del informe)."""

from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from coordinacion.models import EstadoSolicitud, SolicitudReposicion, TipoSolicitud
from core.configuracion import ConfiguracionSistema, EstadoOrden
from core.excepciones import AccesoDenegado, ErrorNegocio, StockInsuficiente
from core.facade import ServicioPosventaFacade
from core.models import Aviso, Bitacora
from inventario.fuentes import FuenteInventario, InventarioExternoAdapter
from inventario.models import Inventario, MovimientoInventario, Repuesto, TipoMovimiento
from inventario.services import ReservaService
from ordenes.dtos import SeguimientoDTO
from ordenes.models import OrdenReparacion

from .fabricas import cargar_demo


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.u = cargar_demo()

    def setUp(self):
        self.f = ServicioPosventaFacade()

    def inv(self, codigo_pieza, centro="MIR"):
        return Inventario.objects.get(repuesto__codigo_pieza=codigo_pieza, centro__codigo=centro)

    def orden(self, codigo):
        return OrdenReparacion.objects.get(codigo=codigo)


class DatosDelDisenoTests(Base):
    def test_estados_iniciales_como_en_el_diseno(self):
        estados = dict(OrdenReparacion.objects.values_list("codigo", "estado"))
        self.assertEqual(estados, {
            "RO-00001": EstadoOrden.RECIBIDA, "RO-00002": EstadoOrden.EN_ESPERA_REPUESTO,
            "RO-00003": EstadoOrden.EN_ESPERA_REPUESTO, "RO-00004": EstadoOrden.EN_REPARACION,
            "RO-00005": EstadoOrden.ENTREGADA})

    def test_reserva_inicial_de_ro_00004(self):
        inv = self.inv("GH96-15845A")
        self.assertEqual((inv.stock_fisico, inv.stock_reservado, inv.disponible), (3, 1, 2))

    def test_singleton_configuracion(self):
        self.assertIs(ConfiguracionSistema(), ConfiguracionSistema())


class AccesoPorRolTests(Base):
    """RF-01 y RNF-01: cada rol entra solo a su módulo."""

    PANTALLAS = {"aquispe": "atencion:mis_reparaciones", "amoreno": "ordenes:bandeja",
                 "ebaigorrea": "inventario:reservas", "scaycho": "coordinacion:solicitudes"}

    def test_cada_rol_entra_solo_a_lo_suyo(self):
        for usuario, propia in self.PANTALLAS.items():
            self.client.force_login(self.u[usuario])
            for otro, pantalla in self.PANTALLAS.items():
                r = self.client.get(reverse(pantalla))
                self.assertEqual(r.status_code, 200 if pantalla == propia else 403, (usuario, pantalla))

    def test_login_redirige_al_panel_del_rol(self):
        r = self.client.post(reverse("personal") + "?area=almacen",
                             {"username": "ebaigorrea", "password": "demo1234"})
        self.assertRedirects(r, reverse("inventario:reservas"))

    def test_login_incorrecto_muestra_error(self):
        r = self.client.post(reverse("inicio"), {"username": "aquispe", "password": "mala"})
        self.assertContains(r, "Usuario o contraseña incorrectos")

    def test_sin_sesion_vuelve_al_inicio(self):
        r = self.client.get(reverse("ordenes:bandeja"))
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r.url.startswith(reverse("inicio")))

    def test_contrasenas_con_hash(self):
        self.assertTrue(self.u["aquispe"].password.startswith("pbkdf2_"))

    def test_registro_de_cliente_nuevo(self):
        r = self.client.post(reverse("atencion:registro"), {
            "username": "mlopez", "first_name": "María", "last_name": "López", "email": "m@serviceflow.test",
            "password1": "clave-segura-77", "password2": "clave-segura-77"})
        self.assertRedirects(r, reverse("atencion:mis_reparaciones"))


class SolicitudClienteTests(Base):
    """CU-02 / RF-04 y CU-04 / RF-05."""

    def test_registrar_solicitud_da_codigo_unico_y_recibida(self):
        dto = self.f.registrar_solicitud(self.u["aquispe"], "Galaxy S23", "No enciende", self.orden("RO-00001").centro_id)
        self.assertEqual(dto.codigo, "RO-00006")
        self.assertEqual(self.orden("RO-00006").estado, EstadoOrden.RECIBIDA)
        self.assertTrue(Bitacora.objects.filter(operacion="REGISTRAR_SOLICITUD", referencia="RO-00006").exists())

    def test_campos_vacios_no_guardan_nada(self):
        antes = OrdenReparacion.objects.count()
        self.client.force_login(self.u["aquispe"])
        r = self.client.post(reverse("atencion:nueva_solicitud"), {"modelo_equipo": "", "falla_reportada": "",
                                                                   "centro": ""})
        self.assertContains(r, "Revisa los campos marcados en rojo")
        self.assertEqual(OrdenReparacion.objects.count(), antes)

    def test_cliente_solo_ve_sus_ordenes(self):
        codigos = [o.codigo for o in self.f.mis_reparaciones(self.u["aquispe"])]
        self.assertEqual(codigos, ["RO-00002", "RO-00001"])
        with self.assertRaises(AccesoDenegado):
            self.f.seguimiento(self.u["aquispe"], "RO-00003")  # es de otro cliente

    def test_detalle_ajeno_no_revela_datos(self):
        self.client.force_login(self.u["aquispe"])
        r = self.client.get(reverse("atencion:detalle", args=["RO-00003"]), follow=True)
        self.assertContains(r, "No encontramos esa reparación en tu cuenta")
        self.assertNotContains(r, "La batería se descarga")

    def test_seguimiento_dto_no_expone_tecnico_ni_stock(self):
        dto = self.f.seguimiento(self.u["aquispe"], "RO-00002")
        self.assertIsInstance(dto, SeguimientoDTO)
        campos = set(dto.__dataclass_fields__)
        self.assertFalse(campos & {"tecnico", "stock", "cliente", "reservas", "repuesto"})
        self.assertEqual(dto.estado_texto, "Esperando un repuesto")
        self.assertIsNone(dto.fecha_estimada)

    def test_cancelar_solo_en_recibida(self):
        self.f.cancelar_solicitud(self.u["aquispe"], "RO-00001")
        self.assertEqual(self.orden("RO-00001").estado, EstadoOrden.CANCELADA)
        with self.assertRaises(ErrorNegocio):
            self.f.cancelar_solicitud(self.u["aquispe"], "RO-00002")


class DiagnosticoTests(Base):
    """RF-07 y RF-08."""

    def test_diagnostico_obligatorio(self):
        with self.assertRaises(ErrorNegocio):
            self.f.diagnosticar(self.u["amoreno"], "RO-00001", "  ", None, 1)

    def test_repuesto_de_otro_modelo_se_rechaza(self):
        a55 = Repuesto.objects.get(codigo_pieza="GH82-33385A")
        with self.assertRaises(ErrorNegocio):
            self.f.diagnosticar(self.u["amoreno"], "RO-00001", "Pantalla dañada", a55.id, 1)

    def test_solo_se_ofrecen_repuestos_compatibles(self):
        b = self.f.bandeja_tecnico(self.u["amoreno"], "todas", "RO-00001")
        self.assertEqual({r.nombre for r in b.repuestos},
                         {"Pantalla completa Galaxy S24 Ultra", "Batería Galaxy S24 Ultra"})

    def test_con_repuesto_espera_y_sin_repuesto_repara(self):
        pantalla = Repuesto.objects.get(codigo_pieza="GH82-33524A")
        self.f.diagnosticar(self.u["amoreno"], "RO-00001", "Digitalizador dañado", pantalla.id, 1)
        self.assertEqual(self.orden("RO-00001").estado, EstadoOrden.EN_ESPERA_REPUESTO)
        dto = self.f.registrar_solicitud(self.u["aquispe"], "Galaxy S23", "Lento", self.orden("RO-00001").centro_id)
        self.f.diagnosticar(self.u["amoreno"], dto.codigo, "Limpieza de software", None, 1)
        self.assertEqual(self.orden(dto.codigo).estado, EstadoOrden.EN_REPARACION)

    def test_tecnico_no_toca_ordenes_de_otro_centro(self):
        with self.assertRaises(AccesoDenegado):
            self.f.registrar_entrega(self.u["amoreno"], "RO-00005")


class ReservaTests(Base):
    """CU-08 / RF-10 / RN-01 / RN-02."""

    def test_reserva_con_stock_pasa_a_reparacion(self):
        r = self.f.reservar(self.u["ebaigorrea"], "RO-00003")
        self.assertTrue(r.exito)
        self.assertEqual(self.orden("RO-00003").estado, EstadoOrden.EN_REPARACION)
        inv = self.inv("EB-BA556ABY")
        self.assertEqual((inv.stock_reservado, inv.disponible), (1, 5))
        self.assertTrue(Bitacora.objects.filter(operacion="RESERVAR_REPUESTO", referencia="RO-00003").exists())

    def test_sin_stock_suficiente_no_reserva_nada(self):
        with self.assertRaises(StockInsuficiente) as ctx:
            self.f.reservar(self.u["ebaigorrea"], "RO-00002")
        self.assertEqual(ctx.exception.faltante, 1)
        self.assertEqual(self.inv("GH82-33385A").stock_reservado, 0)
        self.assertEqual(self.orden("RO-00002").estado, EstadoOrden.EN_ESPERA_REPUESTO)

    def test_sin_diagnostico_no_se_reserva(self):
        with self.assertRaises(ErrorNegocio) as ctx:
            self.f.reservar(self.u["ebaigorrea"], "RO-00001")
        self.assertIn("diagnóstico", str(ctx.exception))

    def test_no_se_reserva_dos_veces(self):
        self.f.reservar(self.u["ebaigorrea"], "RO-00003")
        with self.assertRaises(ErrorNegocio):
            self.f.reservar(self.u["ebaigorrea"], "RO-00003")
        self.assertEqual(self.inv("EB-BA556ABY").stock_reservado, 1)

    def test_aviso_rojo_en_pantalla_de_almacen(self):
        self.client.force_login(self.u["ebaigorrea"])
        r = self.client.post(reverse("inventario:reservar", args=["RO-00002"]), follow=True)
        self.assertContains(r, "No hay stock suficiente")
        self.assertContains(r, "Pedir traslado desde San Isidro")

    def test_adapter_cumple_el_contrato(self):
        class Externo:
            def consultar_stock(self, sku):
                return {"almacenes": [{"nombre": "Almacén central", "id": 99, "libres": "7"}]}

        adapter = InventarioExternoAdapter(Externo(), lambda rid: "X")
        self.assertIsInstance(adapter, FuenteInventario)
        self.assertEqual(ReservaService(fuente=adapter).disponibilidad(1), [("Almacén central", 99, 7)])


class ReposicionTests(Base):
    """CU-10 / CU-11 / RF-12 / RF-13 / RN-03 / RN-04: el recorrido completo de la demo."""

    def test_recorrido_traslado_aprobado(self):
        sis = self.orden("RO-00005").centro_id
        codigo = self.f.solicitar(self.u["ebaigorrea"], "RO-00002", TipoSolicitud.TRASLADO, sis)
        s = SolicitudReposicion.objects.get(codigo=codigo)
        self.assertEqual((s.estado, s.cantidad), (EstadoSolicitud.PENDIENTE, 1))
        with self.assertRaises(ErrorNegocio):  # almacén no puede ejecutar sin autorización
            self.f.ejecutar_solicitud(self.u["ebaigorrea"], codigo)

        self.f.resolver_solicitud(self.u["scaycho"], codigo, aprobar=True)
        self.f.ejecutar_solicitud(self.u["ebaigorrea"], codigo)
        self.assertEqual(self.inv("GH82-33385A", "MIR").stock_fisico, 2)
        self.assertEqual(self.inv("GH82-33385A", "SIS").stock_fisico, 2)
        tipos = set(MovimientoInventario.objects.filter(referencia=codigo).values_list("tipo", flat=True))
        self.assertEqual(tipos, {TipoMovimiento.TRASLADO_SALIDA, TipoMovimiento.TRASLADO_ENTRADA})

        self.f.reservar(self.u["ebaigorrea"], "RO-00002")
        self.f.confirmar_fecha(self.u["amoreno"], "RO-00002", timezone.localdate() + timedelta(days=2))
        self.f.marcar_reparada(self.u["amoreno"], "RO-00002")
        inv = self.inv("GH82-33385A", "MIR")
        self.assertEqual((inv.stock_fisico, inv.stock_reservado), (0, 0))
        dto = self.f.seguimiento(self.u["aquispe"], "RO-00002")
        self.assertEqual(dto.estado, EstadoOrden.REPARADA)
        self.assertIsNotNone(dto.fecha_estimada)

    def test_rechazo_exige_motivo_y_la_orden_sigue_esperando(self):
        codigo = self.f.solicitar(self.u["ebaigorrea"], "RO-00002", TipoSolicitud.REPOSICION)
        with self.assertRaises(ErrorNegocio):
            self.f.resolver_solicitud(self.u["scaycho"], codigo, aprobar=False, motivo="")
        self.f.resolver_solicitud(self.u["scaycho"], codigo, aprobar=False, motivo="Sin presupuesto")
        s = SolicitudReposicion.objects.get(codigo=codigo)
        self.assertEqual((s.estado, s.motivo_decision), (EstadoSolicitud.RECHAZADA, "Sin presupuesto"))
        self.assertEqual(self.inv("GH82-33385A").stock_fisico, 1)
        self.assertEqual(self.orden("RO-00002").estado, EstadoOrden.EN_ESPERA_REPUESTO)

    def test_no_se_duplican_solicitudes(self):
        self.f.solicitar(self.u["ebaigorrea"], "RO-00002", TipoSolicitud.REPOSICION)
        with self.assertRaises(ErrorNegocio):
            self.f.solicitar(self.u["ebaigorrea"], "RO-00002", TipoSolicitud.REPOSICION)

    def test_solo_el_coordinador_aprueba(self):
        codigo = self.f.solicitar(self.u["ebaigorrea"], "RO-00002", TipoSolicitud.REPOSICION)
        self.client.force_login(self.u["ebaigorrea"])
        r = self.client.post(reverse("coordinacion:resolver", args=[codigo]), {"decision": "aprobar"})
        self.assertEqual(r.status_code, 403)


class TecnicoYStockTests(Base):
    def test_marcar_reparada_pide_fecha_confirmada(self):
        self.f.reservar(self.u["ebaigorrea"], "RO-00003")
        with self.assertRaises(ErrorNegocio):
            self.f.marcar_reparada(self.u["amoreno"], "RO-00003")

    def test_fecha_pasada_no_se_acepta(self):
        with self.assertRaises(ErrorNegocio):
            self.f.confirmar_fecha(self.u["amoreno"], "RO-00004", timezone.localdate() - timedelta(days=1))

    def test_ajuste_no_baja_de_lo_reservado(self):
        inv = self.inv("GH96-15845A")
        with self.assertRaises(ErrorNegocio):
            self.f.ajustar_stock(self.u["ebaigorrea"], inv.id, 0, "Conteo físico")
        self.f.ajustar_stock(self.u["ebaigorrea"], inv.id, 5, "Conteo físico")
        self.assertEqual(self.inv("GH96-15845A").stock_fisico, 5)

    def test_ajuste_exige_motivo(self):
        with self.assertRaises(ErrorNegocio):
            self.f.ajustar_stock(self.u["ebaigorrea"], self.inv("EB-BA556ABY").id, 3, "")

    def test_coordinador_cancela_con_motivo(self):
        with self.assertRaises(ErrorNegocio):
            self.f.cancelar_orden(self.u["scaycho"], "RO-00001", "")
        self.f.cancelar_orden(self.u["scaycho"], "RO-00001", "Cliente no trajo el equipo")
        self.assertEqual(self.orden("RO-00001").estado, EstadoOrden.CANCELADA)
        with self.assertRaises(ErrorNegocio):
            self.f.cancelar_orden(self.u["scaycho"], "RO-00004", "No")


class AvisosYBitacoraTests(Base):
    """RF-06 y RF-16."""

    def test_cambio_de_estado_avisa_al_cliente(self):
        mail.outbox = []
        self.f.reservar(self.u["ebaigorrea"], "RO-00003")
        self.assertTrue(Aviso.objects.filter(referencia="RO-00003", asunto="Llegó tu repuesto").exists())
        self.assertEqual(mail.outbox[-1].to, ["jtolentino@serviceflow.test"])

    def test_cliente_ve_sus_avisos_y_se_marcan_leidos(self):
        self.client.force_login(self.u["aquispe"])
        r = self.client.get(reverse("atencion:mis_reparaciones"))
        self.assertContains(r, "sin leer")
        r = self.client.get(reverse("atencion:avisos"))
        self.assertContains(r, "Tu equipo ya tiene diagnóstico")
        self.assertNotContains(r, "RO-00003")  # avisos de otro cliente
        self.assertEqual(Aviso.objects.filter(cliente=self.u["aquispe"], leido=False).count(), 0)

    def test_avisos_en_el_detalle_de_la_orden(self):
        self.client.force_login(self.u["aquispe"])
        r = self.client.get(reverse("atencion:detalle", args=["RO-00002"]))
        self.assertContains(r, "Avisos de esta reparación")
        self.assertContains(r, "Recibimos tu solicitud")

    def test_buscar_por_codigo(self):
        self.client.force_login(self.u["aquispe"])
        r = self.client.get(reverse("atencion:mis_reparaciones") + "?codigo=2")
        self.assertRedirects(r, reverse("atencion:detalle", args=["RO-00002"]))
        r = self.client.get(reverse("atencion:mis_reparaciones") + "?codigo=RO-00003", follow=True)
        self.assertContains(r, "No encontramos esa reparación en tu cuenta")

    def test_cliente_ve_el_diagnostico_tecnico(self):
        dto = self.f.seguimiento(self.u["aquispe"], "RO-00002")
        self.assertEqual(dto.diagnostico, "Panel y digitalizador dañados")
        self.assertIn("Pantalla completa Galaxy A55", dto.pieza)
        self.client.force_login(self.u["aquispe"])
        r = self.client.get(reverse("atencion:detalle", args=["RO-00002"]))
        self.assertContains(r, "Diagnóstico técnico")
        self.assertNotContains(r, "Alessandro")  # el nombre del técnico no se muestra

    def test_filtros_rapidos_del_coordinador(self):
        sis = self.orden("RO-00005").centro_id
        self.f.solicitar(self.u["ebaigorrea"], "RO-00002", TipoSolicitud.TRASLADO, sis)
        visibles, conteos = self.f.solicitudes_pendientes("REPOSICION")
        self.assertEqual((len(visibles), conteos["todas"], conteos["TRASLADO"]), (0, 1, 1))
        visibles, _ = self.f.solicitudes_pendientes("TRASLADO", "Centro Miraflores")
        self.assertEqual(len(visibles), 1)
        self.client.force_login(self.u["scaycho"])
        r = self.client.get(reverse("coordinacion:solicitudes") + "?tipo=REPOSICION")
        self.assertContains(r, "No hay solicitudes con este filtro")

    def test_reservar_desactivado_sin_diagnostico(self):
        self.client.force_login(self.u["ebaigorrea"])
        r = self.client.get(reverse("inventario:reservas"))
        self.assertContains(r, "Sin diagnóstico")
        self.assertContains(r, 'class="btn sm" disabled')

    def test_formulario_de_diagnostico_tiene_cancelar(self):
        self.client.force_login(self.u["amoreno"])
        r = self.client.get(reverse("ordenes:bandeja") + "?orden=RO-00001")
        self.assertContains(r, '<button type="reset"')

    def test_solicitud_resuelta_muestra_su_estado(self):
        codigo = self.f.solicitar(self.u["ebaigorrea"], "RO-00002", TipoSolicitud.REPOSICION)
        self.f.resolver_solicitud(self.u["scaycho"], codigo, aprobar=True)
        with self.assertRaises(ErrorNegocio) as ctx:
            self.f.resolver_solicitud(self.u["scaycho"], codigo, aprobar=False, motivo="Otra vez")
        self.assertIn("Autorizada por Santiago Caycho", str(ctx.exception))

    def test_bitacora_guarda_usuario_y_referencia(self):
        self.f.reservar(self.u["ebaigorrea"], "RO-00003")
        b = Bitacora.objects.filter(operacion="RESERVAR_REPUESTO").first()
        self.assertEqual((b.usuario, b.referencia), (self.u["ebaigorrea"], "RO-00003"))

    def test_pantallas_cargan(self):
        for usuario, urls in {
            "aquispe": ["atencion:mis_reparaciones", "atencion:nueva_solicitud", "atencion:centros"],
            "amoreno": ["ordenes:bandeja", "ordenes:stock"],
            "ebaigorrea": ["inventario:reservas", "inventario:stock", "inventario:ingresos", "inventario:movimientos"],
            "scaycho": ["coordinacion:solicitudes", "coordinacion:reportes", "coordinacion:cancelar"],
        }.items():
            self.client.force_login(self.u[usuario])
            for nombre in urls:
                self.assertEqual(self.client.get(reverse(nombre)).status_code, 200, nombre)
