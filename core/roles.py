"""Roles del sistema (sección 2.2) como grupos de Django, y control de acceso por rol (RNF-01)."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


class Rol:
    CLIENTE = "Cliente"
    TECNICO = "Tecnico"
    ALMACEN = "Almacen"
    COORDINADOR = "Coordinador"

    TODOS = [CLIENTE, TECNICO, ALMACEN, COORDINADOR]
    ETIQUETAS = {CLIENTE: "Cliente", TECNICO: "Técnico", ALMACEN: "Almacén", COORDINADOR: "Coordinador"}
    PANEL = {
        CLIENTE: "atencion:mis_reparaciones",
        TECNICO: "ordenes:bandeja",
        ALMACEN: "inventario:reservas",
        COORDINADOR: "coordinacion:solicitudes",
    }


def rol_de(usuario):
    if not usuario.is_authenticated:
        return None
    nombres = set(usuario.groups.values_list("name", flat=True))
    for rol in Rol.TODOS:
        if rol in nombres:
            return rol
    return None


def rol_requerido(*roles):
    """Decorador de vistas: exige sesión iniciada y uno de los roles indicados."""

    def decorador(vista):
        @login_required
        @wraps(vista)
        def envoltura(request, *args, **kwargs):
            if rol_de(request.user) not in roles:
                raise PermissionDenied("Tu rol no tiene acceso a esta pantalla.")
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
