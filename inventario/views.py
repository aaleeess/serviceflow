"""Panel de almacén (RF-09 a RF-12, CU-08, CU-10)."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from coordinacion.models import TipoSolicitud
from core.excepciones import ErrorNegocio, StockInsuficiente
from core.facade import ServicioPosventaFacade
from core.roles import Rol, rol_requerido


def _a_reservas(codigo=None):
    return redirect(reverse("inventario:reservas") + (f"?orden={codigo}" if codigo else ""))


@rol_requerido(Rol.ALMACEN)
def reservas(request):
    try:
        centro, panel = ServicioPosventaFacade().panel_reservas(
            request.user, request.GET.get("filtro", "todas"), request.GET.get("q", "").strip(),
            request.GET.get("orden"))
    except ErrorNegocio as e:
        messages.error(request, str(e))
        centro, panel = None, None
    return render(request, "almacen/reservas.html", {"centro": centro, "p": panel})


@rol_requerido(Rol.ALMACEN)
@require_POST
def reservar(request, codigo):
    try:
        resultado = ServicioPosventaFacade().reservar(request.user, codigo)
        messages.success(request, resultado.mensaje)
        return _a_reservas()
    except StockInsuficiente as e:
        # Heurística 9: aviso claro en rojo con la salida directa (pedir traslado o reposición).
        messages.error(request, f"{codigo}: {e}")
    except ErrorNegocio as e:
        messages.error(request, str(e))
    return _a_reservas(codigo)


@rol_requerido(Rol.ALMACEN)
@require_POST
def solicitar(request, codigo):
    tipo = request.POST.get("tipo", TipoSolicitud.REPOSICION)
    try:
        sr = ServicioPosventaFacade().solicitar(request.user, codigo, tipo, request.POST.get("centro_origen"))
        que = "el traslado" if tipo == TipoSolicitud.TRASLADO else "la reposición"
        messages.success(request, f"Pediste {que} ({sr}). El coordinador debe aprobarlo; mientras tanto "
                                  f"{codigo} sigue en espera de repuesto.")
    except ErrorNegocio as e:
        messages.error(request, str(e))
    return _a_reservas(codigo)


@rol_requerido(Rol.ALMACEN)
def stock(request):
    try:
        centro, filas = ServicioPosventaFacade().stock_del_centro(request.user)
    except ErrorNegocio as e:
        messages.error(request, str(e))
        centro, filas = None, []
    return render(request, "tecnico/stock.html", {"centro": centro, "filas": filas, "editable": True})


@rol_requerido(Rol.ALMACEN)
@require_POST
def ajustar(request):
    try:
        ServicioPosventaFacade().ajustar_stock(request.user, request.POST.get("inventario"),
                                               request.POST.get("cantidad"), request.POST.get("motivo"))
        messages.success(request, "Ajustaste el stock. El cambio quedó en Movimientos.")
    except ErrorNegocio as e:
        messages.error(request, str(e))
    return redirect("inventario:stock")


@rol_requerido(Rol.ALMACEN)
def ingresos(request):
    try:
        autorizadas = ServicioPosventaFacade().autorizadas(request.user)
    except ErrorNegocio as e:
        messages.error(request, str(e))
        autorizadas = []
    return render(request, "almacen/ingresos.html", {"autorizadas": autorizadas})


@rol_requerido(Rol.ALMACEN)
@require_POST
def ejecutar(request, codigo):
    try:
        ServicioPosventaFacade().ejecutar_solicitud(request.user, codigo)
        messages.success(request, f"Registraste {codigo}. El stock ya entró al centro: ahora puedes reservar.")
        return redirect("inventario:reservas")
    except ErrorNegocio as e:
        messages.error(request, str(e))
    return redirect("inventario:ingresos")


@rol_requerido(Rol.ALMACEN)
def movimientos(request):
    try:
        lista = ServicioPosventaFacade().movimientos(request.user)
    except ErrorNegocio as e:
        messages.error(request, str(e))
        lista = []
    return render(request, "almacen/movimientos.html", {"movimientos": lista})
