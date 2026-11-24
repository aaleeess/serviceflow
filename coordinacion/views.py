"""Panel del coordinador (RF-13, RF-15, CU-11)."""

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from core.excepciones import ErrorNegocio
from core.facade import ServicioPosventaFacade
from core.roles import Rol, rol_requerido


@rol_requerido(Rol.COORDINADOR)
def solicitudes(request):
    facade = ServicioPosventaFacade()
    tipo, centro = request.GET.get("tipo", ""), request.GET.get("centro", "")
    pendientes, conteos = facade.solicitudes_pendientes(tipo, centro)
    return render(request, "coordinacion/solicitudes.html",
                  {"pendientes": pendientes, "conteos": conteos, "tipo": tipo, "centro": centro,
                   "r": facade.reportes_generales()})


@rol_requerido(Rol.COORDINADOR)
@require_POST
def resolver(request, codigo):
    aprobar = request.POST.get("decision") == "aprobar"
    try:
        ServicioPosventaFacade().resolver_solicitud(request.user, codigo, aprobar, request.POST.get("motivo", ""))
        if aprobar:
            messages.success(request, f"Aprobaste {codigo}. Almacén ya puede registrar el movimiento.")
        else:
            messages.success(request, f"Rechazaste {codigo}. La orden sigue esperando el repuesto.")
    except ErrorNegocio as e:
        messages.error(request, str(e))
    return redirect("coordinacion:solicitudes")


@rol_requerido(Rol.COORDINADOR)
def reportes(request):
    return render(request, "coordinacion/reportes.html", {"r": ServicioPosventaFacade().reportes_generales()})


@rol_requerido(Rol.COORDINADOR)
def cancelar(request):
    facade = ServicioPosventaFacade()
    if request.method == "POST":
        codigo = request.POST.get("codigo", "")
        try:
            facade.cancelar_orden(request.user, codigo, request.POST.get("motivo", ""))
            messages.success(request, f"Cancelaste {codigo}. Se avisó al cliente.")
        except ErrorNegocio as e:
            messages.error(request, str(e))
        return redirect("coordinacion:cancelar")
    return render(request, "coordinacion/cancelar.html", {"ordenes": facade.ordenes_cancelables()})
