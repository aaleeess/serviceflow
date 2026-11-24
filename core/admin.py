from django.contrib import admin

from .models import Aviso, Bitacora, PerfilEmpleado


@admin.register(PerfilEmpleado)
class PerfilEmpleadoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "centro")
    list_filter = ("centro",)


@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    """Bitácora de solo lectura (RF-16, RN-05): demuestra la trazabilidad."""

    list_display = ("fecha", "usuario", "operacion", "referencia", "detalle")
    list_filter = ("operacion",)
    search_fields = ("referencia", "detalle")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Aviso)
class AvisoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "cliente", "referencia", "asunto")
    search_fields = ("referencia",)

    def has_change_permission(self, request, obj=None):
        return False
