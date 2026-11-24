from django.contrib import admin

from .models import SolicitudReposicion


@admin.register(SolicitudReposicion)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ("codigo", "tipo", "repuesto", "cantidad", "centro", "centro_origen", "estado", "creada")
    list_filter = ("estado", "tipo")
