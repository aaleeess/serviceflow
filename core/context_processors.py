"""Datos de la persona conectada y el menú lateral de su rol (mismo menú en todas sus pantallas)."""

from core.configuracion import EstadoOrden
from core.repositories import PerfilRepository
from core.roles import Rol, rol_de

AVATAR = {Rol.CLIENTE: "cliente", Rol.TECNICO: "c-tecnico", Rol.ALMACEN: "c-almacen",
          Rol.COORDINADOR: "c-coordinacion"}


def _contadores(usuario, rol, centro):
    """Números pequeños del menú. Solo lectura."""
    from coordinacion.models import EstadoSolicitud, SolicitudReposicion
    from ordenes.models import OrdenReparacion

    if rol == Rol.TECNICO and centro:
        return {"ordenes": OrdenReparacion.objects.filter(centro=centro, estado__in=EstadoOrden.ABIERTOS).count()}
    if rol == Rol.ALMACEN and centro:
        return {
            "reservas": OrdenReparacion.objects.filter(centro=centro, estado=EstadoOrden.EN_ESPERA_REPUESTO,
                                                       diagnostico__repuesto__isnull=False).count(),
            "ingresos": SolicitudReposicion.objects.filter(centro=centro, estado=EstadoSolicitud.AUTORIZADA).count(),
        }
    if rol == Rol.COORDINADOR:
        return {"solicitudes": SolicitudReposicion.objects.filter(estado=EstadoSolicitud.PENDIENTE).count()}
    return {}


def _menu(rol, cuenta):
    if rol == Rol.TECNICO:
        return [("ordenes:bandeja", "Órdenes", "llave", cuenta.get("ordenes")),
                ("ordenes:stock", "Stock del centro", "cuadros", None)]
    if rol == Rol.ALMACEN:
        return [("inventario:reservas", "Reservas", "caja", cuenta.get("reservas")),
                ("inventario:stock", "Stock del centro", "cuadros", None),
                ("inventario:ingresos", "Registrar ingreso", "mas", cuenta.get("ingresos")),
                ("inventario:movimientos", "Movimientos", "flechas", None)]
    if rol == Rol.COORDINADOR:
        return [("coordinacion:solicitudes", "Solicitudes", "aprobar", cuenta.get("solicitudes")),
                ("coordinacion:reportes", "Reportes", "barras", None),
                ("coordinacion:cancelar", "Cancelar órdenes", "prohibido", None)]
    return []


def sesion(request):
    usuario = getattr(request, "user", None)
    if usuario is None or not usuario.is_authenticated:
        return {}
    rol = rol_de(usuario)
    centro = PerfilRepository().centro_de(usuario) if rol in (Rol.TECNICO, Rol.ALMACEN, Rol.COORDINADOR) else None
    nombre = usuario.get_full_name() or usuario.username
    subtitulo = Rol.ETIQUETAS.get(rol, "")
    if centro:
        subtitulo += f", {centro.nombre.replace('Centro ', '')}"
    actual = ""
    if request.resolver_match:
        actual = f"{request.resolver_match.namespace}:{request.resolver_match.url_name}"
    menu = [{"url": u, "texto": t, "icono": i, "badge": b, "activo": u == actual}
            for u, t, i, b in _menu(rol, _contadores(usuario, rol, centro))]
    avisos_nuevos = 0
    if rol == Rol.CLIENTE:
        from core.avisos import AvisoService

        avisos_nuevos = AvisoService().cuantos_nuevos(usuario)
    return {"sesion": {"nombre": nombre, "rol": rol, "rol_etiqueta": Rol.ETIQUETAS.get(rol, ""),
                       "subtitulo": subtitulo, "avatar": AVATAR.get(rol, "cliente"), "menu": menu,
                       "centro": centro, "avisos_nuevos": avisos_nuevos, "actual": actual}}
