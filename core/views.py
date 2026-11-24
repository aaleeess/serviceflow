"""Inicio, acceso del personal por área y redirección al panel de cada rol (RF-01)."""

from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .roles import Rol, rol_de

AREAS = [
    {"id": "tecnico", "nombre": "Técnica", "icono": "llave",
     "resumen": "Diagnóstico y reparación de los equipos del centro.",
     "tareas": ["Diagnosticar equipos", "Confirmar fechas de entrega", "Marcar reparaciones terminadas"],
     "ejemplo": "Ejemplo: amoreno"},
    {"id": "almacen", "nombre": "Almacén", "icono": "caja",
     "resumen": "Repuestos, reservas y stock de cada centro.",
     "tareas": ["Reservar repuestos", "Pedir traslados o reposición", "Registrar ingresos de stock"],
     "ejemplo": "Ejemplo: ebaigorrea"},
    {"id": "coordinacion", "nombre": "Coordinación", "icono": "aprobar",
     "resumen": "Aprobaciones y seguimiento de los dos centros.",
     "tareas": ["Aprobar reposiciones y traslados", "Revisar reportes", "Cancelar órdenes"],
     "ejemplo": "Ejemplo: scaycho"},
    {"id": "administracion", "nombre": "Administración", "icono": "escudo",
     "resumen": "Usuarios, roles y datos generales del sistema.",
     "tareas": ["Gestionar usuarios y roles", "Editar centros y repuestos", "Revisar la bitácora"],
     "ejemplo": "Ejemplo: admin"},
]


def _destino(usuario):
    rol = rol_de(usuario)
    if rol:
        return reverse(Rol.PANEL[rol])
    if usuario.is_staff:
        return reverse("admin:index")
    return reverse("sin_rol")


def _ingresar(request, plantilla, contexto):
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(_destino(form.get_user()))
    contexto.update({"form": form, "error": request.method == "POST"})
    return render(request, plantilla, contexto)


def inicio(request):
    """Pantalla de inicio y acceso de clientes (Figura 4)."""
    if request.user.is_authenticated and request.method == "GET":
        return redirect(_destino(request.user))
    return _ingresar(request, "publico/inicio.html", {})


def personal(request):
    """Acceso del personal: primero el área, luego usuario y contraseña."""
    if request.user.is_authenticated and request.method == "GET":
        return redirect(_destino(request.user))
    area = next((a for a in AREAS if a["id"] == request.GET.get("area")), None)
    return _ingresar(request, "publico/personal.html", {"areas": AREAS, "area": area})


def panel(request):
    if not request.user.is_authenticated:
        return redirect("inicio")
    return redirect(_destino(request.user))


def sin_rol(request):
    return render(request, "publico/sin_rol.html")


@require_POST
def salir(request):
    logout(request)
    return redirect("inicio")
