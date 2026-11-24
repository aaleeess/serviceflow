from django.urls import path

from . import views

app_name = "atencion"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("", views.mis_reparaciones, name="mis_reparaciones"),
    path("nueva/", views.nueva_solicitud, name="nueva_solicitud"),
    path("centros/", views.centros, name="centros"),
    path("avisos/", views.avisos, name="avisos"),
    path("orden/<str:codigo>/", views.detalle, name="detalle"),
    path("orden/<str:codigo>/cancelar/", views.cancelar, name="cancelar"),
]
