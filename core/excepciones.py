"""Errores de negocio. Las vistas los muestran como mensajes claros (heurística 9 de Nielsen)."""


class ErrorNegocio(Exception):
    """Una regla de negocio impidió la operación."""


class StockInsuficiente(ErrorNegocio):
    def __init__(self, mensaje, faltante=0):
        super().__init__(mensaje)
        self.faltante = faltante


class AccesoDenegado(ErrorNegocio):
    """El usuario no puede ver o modificar ese recurso (RN-06, RNF-08)."""
