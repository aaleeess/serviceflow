"""Carga los datos ficticios del piloto, iguales a los del diseño final.

Uso:  python manage.py seed_demo            (solo si la base está vacía)
      python manage.py seed_demo --reiniciar (borra todo y vuelve a cargar)

Las órdenes se crean con los mismos servicios que usan las pantallas, así el historial,
la bitácora y el stock quedan coherentes con las reglas del sistema.
"""

from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Aviso, PerfilEmpleado
from core.roles import Rol
from inventario.models import CentroServicio, Inventario, Repuesto
from ordenes.models import HistorialEstado, OrdenReparacion

CLAVE = "demo1234"

USUARIOS = [
    # usuario, nombre, apellido, rol, centro
    ("aquispe", "Álvaro", "Quispe", Rol.CLIENTE, None),
    ("jtolentino", "Junior", "Tolentino", Rol.CLIENTE, None),
    ("amoreno", "Alessandro", "Moreno", Rol.TECNICO, "MIR"),
    ("lramos", "Lucía", "Ramos", Rol.TECNICO, "SIS"),
    ("ebaigorrea", "Erick", "Baigorrea", Rol.ALMACEN, "MIR"),
    ("scaycho", "Santiago", "Caycho", Rol.COORDINADOR, None),
]

REPUESTOS = [
    # código, nombre, compatibilidad, stock Miraflores, stock San Isidro
    ("GH82-33385A", "Pantalla completa Galaxy A55", "Galaxy A55", 1, 3),
    ("EB-BA556ABY", "Batería Galaxy A55", "Galaxy A55", 6, 4),
    ("GH96-16112A", "Cámara trasera Galaxy A55", "Galaxy A55", 2, 1),
    ("GH82-31201A", "Pantalla completa Galaxy A54", "Galaxy A54", 0, 2),
    ("GH96-15890A", "Placa de carga USB-C Galaxy A54", "Galaxy A54", 1, 2),
    ("GH96-15845A", "Placa de carga USB-C Galaxy S23", "Galaxy S23", 3, 2),
    ("EB-BS912ABY", "Batería Galaxy S23", "Galaxy S23", 2, 3),
    ("GH82-30480A", "Pantalla completa Galaxy S23", "Galaxy S23", 2, 1),
    ("GH82-33524A", "Pantalla completa Galaxy S24 Ultra", "Galaxy S24 Ultra", 4, 1),
    ("EB-BS928ABY", "Batería Galaxy S24 Ultra", "Galaxy S24 Ultra", 3, 2),
]


class Command(BaseCommand):
    help = "Carga usuarios, centros, repuestos y las órdenes RO-00001 a RO-00005 del diseño."

    def add_arguments(self, parser):
        parser.add_argument("--reiniciar", action="store_true", help="Borra todos los datos antes de cargar.")

    def handle(self, *args, **options):
        from django.test.utils import override_settings

        # Los avisos de la carga inicial no se imprimen como correos.
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"):
            self._cargar(**options)

    def _cargar(self, reiniciar=False, **options):
        if reiniciar:
            call_command("flush", interactive=False, verbosity=0)
        elif User.objects.exists() or OrdenReparacion.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Ya hay datos. Para empezar de cero usa: python manage.py seed_demo --reiniciar"))
            return

        from core.facade import ServicioPosventaFacade

        grupos = {r: Group.objects.get_or_create(name=r)[0] for r in Rol.TODOS}
        mir = CentroServicio.objects.create(codigo="MIR", nombre="Centro Miraflores",
                                            direccion="Av. José Larco 345, Miraflores (ficticio)",
                                            horario_atencion="Lun a sáb, 9:00 a 19:00")
        sis = CentroServicio.objects.create(codigo="SIS", nombre="Centro San Isidro",
                                            direccion="Av. Javier Prado Oeste 1200, San Isidro (ficticio)",
                                            horario_atencion="Lun a vie, 9:00 a 18:00")
        centros = {"MIR": mir, "SIS": sis}

        u = {}
        admin = User.objects.create_superuser("admin", "admin@serviceflow.test", CLAVE,
                                              first_name="Administrador")
        u["admin"] = admin
        for usuario, nombre, apellido, rol, centro in USUARIOS:
            persona = User.objects.create_user(usuario, f"{usuario}@serviceflow.test", CLAVE,
                                               first_name=nombre, last_name=apellido)
            persona.groups.add(grupos[rol])
            if rol != Rol.CLIENTE:
                PerfilEmpleado.objects.create(usuario=persona, centro=centros.get(centro))
            u[usuario] = persona

        rep = {}
        for codigo, nombre, compat, st_mir, st_sis in REPUESTOS:
            r = Repuesto.objects.create(codigo_pieza=codigo, nombre=nombre, compatibilidad=compat)
            Inventario.objects.create(repuesto=r, centro=mir, stock_fisico=st_mir)
            Inventario.objects.create(repuesto=r, centro=sis, stock_fisico=st_sis)
            rep[codigo] = r

        f = ServicioPosventaFacade()
        hoy = timezone.localdate()

        # RO-00001: recién registrada (Recibida)
        f.registrar_solicitud(u["aquispe"], "Galaxy S24 Ultra", "La pantalla no responde al tacto.", mir.id)
        # RO-00002: necesita 2 pantallas y Miraflores tiene 1 (caso de la demo)
        f.registrar_solicitud(u["aquispe"], "Galaxy A55 5G", "Pantalla rota tras una caída.", mir.id)
        f.diagnosticar(u["amoreno"], "RO-00002", "Panel y digitalizador dañados",
                       rep["GH82-33385A"].id, 2)
        # RO-00003: hay stock, lista para reservar
        f.registrar_solicitud(u["jtolentino"], "Galaxy A55 5G", "La batería se descarga en dos horas.", mir.id)
        f.diagnosticar(u["amoreno"], "RO-00003", "Batería degradada, retiene 60 % de su carga",
                       rep["EB-BA556ABY"].id, 1)
        # RO-00004: en reparación con fecha confirmada
        f.registrar_solicitud(u["jtolentino"], "Galaxy S23", "No carga con ningún cable.", mir.id)
        f.diagnosticar(u["amoreno"], "RO-00004", "Puerto de carga dañado por humedad", rep["GH96-15845A"].id, 1)
        f.reservar(u["ebaigorrea"], "RO-00004")
        f.confirmar_fecha(u["amoreno"], "RO-00004", hoy + timedelta(days=3))
        # RO-00005: entregada en San Isidro, sin repuesto
        f.registrar_solicitud(u["jtolentino"], "Galaxy A54", "Se reinicia solo varias veces al día.", sis.id)
        f.diagnosticar(u["lramos"], "RO-00005", "Falla de software; se reinstaló el sistema", None, 1)
        f.confirmar_fecha(u["lramos"], "RO-00005", hoy)
        f.marcar_reparada(u["lramos"], "RO-00005")
        f.registrar_entrega(u["lramos"], "RO-00005")

        self._ajustar_horas()
        self.stdout.write(self.style.SUCCESS(
            "Datos cargados. Usuarios (contraseña demo1234): aquispe, jtolentino, amoreno, lramos, "
            "ebaigorrea, scaycho y admin."))

    def _ajustar_horas(self):
        """Deja horas parecidas a las del diseño (registrada 09:58, evaluación 10:15, etc.)."""
        ahora = timezone.now()
        minutos = {
            "RO-00001": [40],
            "RO-00002": [85, 68, 25, 25],
            "RO-00003": [60, 18, 18],
            "RO-00004": [2 * 24 * 60, 2 * 24 * 60 - 30, 2 * 24 * 60 - 31, 2 * 24 * 60 - 120, 2 * 24 * 60 - 140],
            "RO-00005": [5 * 24 * 60, 5 * 24 * 60 - 60, 5 * 24 * 60 - 61, 5 * 24 * 60 - 90, 4 * 24 * 60, 3 * 24 * 60],
        }
        for codigo, lista in minutos.items():
            orden = OrdenReparacion.objects.get(codigo=codigo)
            historial = list(HistorialEstado.objects.filter(orden=orden).order_by("id"))
            nuevas = {}
            for h, m in zip(historial, lista):
                nuevas[h.pk] = ahora - timedelta(minutes=m)
                HistorialEstado.objects.filter(pk=h.pk).update(fecha=nuevas[h.pk])
            # Cada aviso toma la hora del paso del historial que lo generó.
            for aviso in Aviso.objects.filter(referencia=codigo):
                origen = [h for h in historial if h.fecha <= aviso.fecha and h.pk in nuevas]
                if origen:
                    Aviso.objects.filter(pk=aviso.pk).update(
                        fecha=nuevas[origen[-1].pk], leido=codigo in ("RO-00004", "RO-00005"))
            OrdenReparacion.objects.filter(pk=orden.pk).update(
                creada=ahora - timedelta(minutes=lista[0]), actualizada=ahora - timedelta(minutes=lista[-1]))
