"""Portal del cliente (RF-02 a RF-05, CU-02, CU-04). Las vistas solo hablan con la Facade."""

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.excepciones import AccesoDenegado, ErrorNegocio
from core.facade import ServicioPosventaFacade
from core.roles import Rol, rol_requerido

from .forms import RegistroForm, SolicitudForm


def registro(request):
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            usuario = form.save()
            usuario.groups.add(Group.objects.get_or_create(name=Rol.CLIENTE)[0])
        login(request, usuario)
        messages.success(request, "Tu cuenta está lista. Ya puedes registrar tu primera reparación.")
        return redirect("atencion:mis_reparaciones")
    return render(request, "cliente/registro.html", {"form": form})


@rol_requerido(Rol.CLIENTE)
def mis_reparaciones(request):
    facade = ServicioPosventaFacade()
    ordenes = facade.mis_reparaciones(request.user)
    buscado = request.GET.get("codigo", "").strip().upper()
    if buscado:
        # CU-04 paso 1: el cliente busca por código dentro de "Mis reparaciones".
        if buscado.isdigit():
            buscado = f"RO-{int(buscado):05d}"
        if any(o.codigo == buscado for o in ordenes):
            return redirect("atencion:detalle", codigo=buscado)
        messages.error(request, "No encontramos esa reparación en tu cuenta.")
    novedades = [a for a in facade.avisos(request.user) if a.nuevo][:3]
    centros = {o.centro for o in ordenes if not o.cancelada}
    return render(request, "cliente/mis_reparaciones.html",
                  {"ordenes": ordenes, "centros_cliente": centros, "novedades": novedades, "buscado": buscado})


@rol_requerido(Rol.CLIENTE)
def detalle(request, codigo):
    facade = ServicioPosventaFacade()
    try:
        orden = facade.seguimiento(request.user, codigo)
        avisos = facade.avisos_de_orden(request.user, codigo)
    except AccesoDenegado as e:
        # CU-04 flujo alternativo: mensaje sin exponer información ajena.
        messages.error(request, str(e))
        return redirect("atencion:mis_reparaciones")
    return render(request, "cliente/detalle.html", {"orden": orden, "avisos": avisos})


@rol_requerido(Rol.CLIENTE)
def avisos(request):
    return render(request, "cliente/avisos.html",
                  {"avisos": ServicioPosventaFacade().avisos(request.user, marcar_leidos=True)})


@rol_requerido(Rol.CLIENTE)
def nueva_solicitud(request):
    facade = ServicioPosventaFacade()
    form = SolicitudForm(request.POST or None, centros=facade.centros())
    if request.method == "POST" and form.is_valid():
        try:
            dto = facade.registrar_solicitud(request.user, form.cleaned_data["modelo_equipo"],
                                             form.cleaned_data["falla_reportada"], form.cleaned_data["centro"])
        except ErrorNegocio as e:
            form.add_error(None, str(e))
        else:
            messages.success(request, f"Registramos tu solicitud. Tu código es {dto.codigo} y está {dto.estado_texto}.")
            return redirect("atencion:detalle", codigo=dto.codigo)
    return render(request, "cliente/nueva_solicitud.html", {"form": form})


@rol_requerido(Rol.CLIENTE)
@require_POST
def cancelar(request, codigo):
    try:
        ServicioPosventaFacade().cancelar_solicitud(request.user, codigo, request.POST.get("motivo", ""))
        messages.success(request, f"Cancelaste la solicitud {codigo}.")
    except ErrorNegocio as e:
        messages.error(request, str(e))
    return redirect("atencion:mis_reparaciones")


@rol_requerido(Rol.CLIENTE)
def centros(request):
    return render(request, "cliente/centros.html", {"centros": ServicioPosventaFacade().centros()})
