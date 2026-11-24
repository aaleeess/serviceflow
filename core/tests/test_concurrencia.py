"""Dos reservas al mismo tiempo por la última unidad (RNF-06, sección 2.7).

Corre con MySQL / MariaDB (InnoDB) o PostgreSQL. En SQLite select_for_update() no bloquea
filas, así que ahí se omite.
"""

import threading
import unittest

from django.db import connection
from django.test import TransactionTestCase

from core.excepciones import ErrorNegocio
from core.facade import ServicioPosventaFacade
from inventario.models import Inventario, Reserva
from ordenes.models import OrdenReparacion

from .fabricas import cargar_demo


@unittest.skipIf(connection.vendor == "sqlite", "La prueba de concurrencia necesita MySQL o PostgreSQL.")
class ConcurrenciaTests(TransactionTestCase):
    def test_solo_una_reserva_por_la_ultima_unidad(self):
        u = cargar_demo()
        f = ServicioPosventaFacade()
        inv = Inventario.objects.get(repuesto__codigo_pieza="EB-BA556ABY", centro__codigo="MIR")
        inv.stock_fisico = 1
        inv.save()
        otra = f.registrar_solicitud(u["aquispe"], "Galaxy A55 5G", "Batería", inv.centro_id).codigo
        f.diagnosticar(u["amoreno"], otra, "Batería degradada", inv.repuesto_id, 1)

        resultados = []

        def reservar(codigo):
            try:
                f.reservar(u["ebaigorrea"], codigo)
                resultados.append("ok")
            except ErrorNegocio:
                resultados.append("sin stock")
            finally:
                connection.close()

        hilos = [threading.Thread(target=reservar, args=(c,)) for c in ("RO-00003", otra)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        self.assertEqual(sorted(resultados), ["ok", "sin stock"])
        inv.refresh_from_db()
        self.assertEqual((inv.stock_reservado, inv.disponible), (1, 0))
        self.assertEqual(Reserva.objects.filter(inventario=inv).count(), 1)
        self.assertEqual(OrdenReparacion.objects.filter(codigo__in=["RO-00003", otra],
                                                        estado="EN_REPARACION").count(), 1)
