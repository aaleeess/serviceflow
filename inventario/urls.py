from django.urls import path

from . import views

app_name = "inventario"

urlpatterns = [
    path("", views.reservas, name="reservas"),
    path("orden/<str:codigo>/reservar/", views.reservar, name="reservar"),
    path("orden/<str:codigo>/solicitar/", views.solicitar, name="solicitar"),
    path("stock/", views.stock, name="stock"),
    path("stock/ajustar/", views.ajustar, name="ajustar"),
    path("ingresos/", views.ingresos, name="ingresos"),
    path("ingresos/<str:codigo>/", views.ejecutar, name="ejecutar"),
    path("movimientos/", views.movimientos, name="movimientos"),
]
