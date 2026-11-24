from django.urls import path

from . import views

app_name = "ordenes"

urlpatterns = [
    path("", views.bandeja, name="bandeja"),
    path("stock/", views.stock, name="stock"),
    path("orden/<str:codigo>/diagnostico/", views.diagnosticar, name="diagnosticar"),
    path("orden/<str:codigo>/fecha/", views.confirmar_fecha, name="confirmar_fecha"),
    path("orden/<str:codigo>/reparada/", views.marcar_reparada, name="marcar_reparada"),
    path("orden/<str:codigo>/entrega/", views.entregar, name="entregar"),
]
