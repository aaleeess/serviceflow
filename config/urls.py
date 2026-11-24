from django.contrib import admin
from django.urls import include, path

from core import views as core

admin.site.site_header = "ServiceFlow · Administración"
admin.site.site_title = "ServiceFlow"
admin.site.index_title = "Datos del sistema"

urlpatterns = [
    path("", core.inicio, name="inicio"),
    path("personal/", core.personal, name="personal"),
    path("panel/", core.panel, name="panel"),
    path("sin-rol/", core.sin_rol, name="sin_rol"),
    path("salir/", core.salir, name="salir"),
    path("cliente/", include("atencion.urls")),
    path("tecnico/", include("ordenes.urls")),
    path("almacen/", include("inventario.urls")),
    path("coordinacion/", include("coordinacion.urls")),
    path("admin/", admin.site.urls),
]

handler403 = "core.views_errores.sin_permiso"
