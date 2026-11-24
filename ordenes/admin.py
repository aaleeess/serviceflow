from django.contrib import admin

from .models import Diagnostico, HistorialEstado, OrdenReparacion


class HistorialInline(admin.TabularInline):
    model = HistorialEstado
    extra = 0
    readonly_fields = ("fecha", "estado_anterior", "estado_nuevo", "descripcion", "motivo", "usuario")
    can_delete = False


@admin.register(OrdenReparacion)
class OrdenAdmin(admin.ModelAdmin):
    list_display = ("codigo", "cliente", "modelo_equipo", "centro", "estado", "fecha_estimada")
    list_filter = ("estado", "centro")
    search_fields = ("codigo", "modelo_equipo")
    inlines = [HistorialInline]


@admin.register(Diagnostico)
class DiagnosticoAdmin(admin.ModelAdmin):
    list_display = ("orden", "tecnico", "repuesto", "cantidad", "fecha")


@admin.register(HistorialEstado)
class HistorialAdmin(admin.ModelAdmin):
    list_display = ("orden", "fecha", "estado_nuevo", "descripcion", "usuario")
