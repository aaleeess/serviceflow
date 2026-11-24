from django.urls import path

from . import views

app_name = "coordinacion"

urlpatterns = [
    path("", views.solicitudes, name="solicitudes"),
    path("solicitud/<str:codigo>/", views.resolver, name="resolver"),
    path("reportes/", views.reportes, name="reportes"),
    path("cancelar/", views.cancelar, name="cancelar"),
]
