"""Datos mínimos para las pruebas: se cargan con el mismo comando de la demo."""

from django.contrib.auth.models import User
from django.core.management import call_command


def cargar_demo():
    call_command("seed_demo", verbosity=0)
    return {u.username: u for u in User.objects.all()}
