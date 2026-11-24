from django.contrib import admin

from .models import CentroServicio, Inventario, MovimientoInventario, Repuesto, Reserva


@admin.register(CentroServicio)
class CentroAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "horario_atencion")


@admin.register(Repuesto)
class RepuestoAdmin(admin.ModelAdmin):
    list_display = ("codigo_pieza", "nombre", "compatibilidad")
    search_fields = ("nombre", "codigo_pieza")


@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display = ("repuesto", "centro", "stock_fisico", "stock_reservado", "disponible")
    list_filter = ("centro",)


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("orden", "inventario", "cantidad", "consumida", "fecha")


@admin.register(MovimientoInventario)
class MovimientoAdmin(admin.ModelAdmin):
    list_display = ("fecha", "tipo", "inventario", "cantidad", "usuario", "referencia")
    list_filter = ("tipo",)
