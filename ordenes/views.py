"""Panel del técnico (RF-07, RF-08, RF-09, RF-14)."""

from datetime import date

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.excepciones import ErrorNegocio
from core.facade import ServicioPosventaFacade
from core.roles import Rol, rol_requerido


def _volver(request, codigo=None):
    url = reverse("ordenes:bandeja")
    filtro = request.POST.get("filtro") or request.GET.get("filtro")
    partes = [f"filtro={filtro}"] if filtro else []
    if codigo:
        partes.append(f"orden={codigo}")
    return redirect(url + ("?" + "&".join(partes) if partes else ""))


@rol_requerido(Rol.TECNICO)
def bandeja(request):
    try:
        datos = ServicioPosventaFacade().bandeja_tecnico(request.user, request.GET.get("filtro", "todas"),
                                                         request.GET.get("orden"))
    except ErrorNegocio as e:
        messages.error(request, str(e))
        datos = None
    return render(request, "tecnico/bandeja.html", {"b": datos, "hoy": date.today()})


@rol_requerido(Rol.TECNICO)
@require_POST
def diagnosticar(request, codigo):
    try:
        ServicioPosventaFacade().diagnosticar(request.user, codigo, request.POST.get("descripcion"),
                                              request.POST.get("repuesto") or None, request.POST.get("cantidad") or 1)
        messages.success(request, f"Guardaste el diagnóstico de {codigo}.")
        return _volver(request)
    except (ErrorNegocio, ValueError) as e:
        messages.error(request, str(e) if isinstance(e, ErrorNegocio) else "Revisa la cantidad.")
        return _volver(request, codigo)


@rol_requerido(Rol.TECNICO)
@require_POST
def confirmar_fecha(request, codigo):
    try:
        fecha = date.fromisoformat(request.POST.get("fecha", ""))
    except ValueError:
        fecha = None
    try:
        ServicioPosventaFacade().confirmar_fecha(request.user, codigo, fecha)
        messages.success(request, f"Confirmaste la fecha de entrega de {codigo}. El cliente ya la ve.")
    except ErrorNegocio as e:
        messages.error(request, str(e))
    return _volver(request, codigo)


@rol_requerido(Rol.TECNICO)
@require_POST
def marcar_reparada(request, codigo):
    try:
        ServicioPosventaFacade().marcar_reparada(request.user, codigo)
        messages.success(request, f"{codigo} quedó Reparada. La pieza se descontó del stock.")
    except ErrorNegocio as e:
        messages.error(request, str(e))
    return _volver(request, codigo)


@rol_requerido(Rol.TECNICO)
@require_POST
def entregar(request, codigo):
    try:
        ServicioPosventaFacade().registrar_entrega(request.user, codigo)
        messages.success(request, f"Registraste la entrega de {codigo}.")
    except ErrorNegocio as e:
        messages.error(request, str(e))
    return _volver(request)


@rol_requerido(Rol.TECNICO)
def stock(request):
    try:
        centro, filas = ServicioPosventaFacade().stock_del_centro(request.user)
    except ErrorNegocio as e:
        messages.error(request, str(e))
        centro, filas = None, []
    return render(request, "tecnico/stock.html", {"centro": centro, "filas": filas, "editable": False})
