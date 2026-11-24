"""Configuración general del prototipo.

Patrón creacional Singleton (sección 4.3): ConfiguracionSistema tiene una sola instancia
durante la ejecución, así todos los módulos consultan los mismos estados y parámetros.
"""

from threading import Lock


class EstadoOrden:
    RECIBIDA = "RECIBIDA"
    EN_EVALUACION = "EN_EVALUACION"
    EN_ESPERA_REPUESTO = "EN_ESPERA_REPUESTO"
    EN_REPARACION = "EN_REPARACION"
    REPARADA = "REPARADA"
    ENTREGADA = "ENTREGADA"
    CANCELADA = "CANCELADA"

    CHOICES = [
        (RECIBIDA, "Recibida"),
        (EN_EVALUACION, "En evaluación"),
        (EN_ESPERA_REPUESTO, "En espera de repuesto"),
        (EN_REPARACION, "En reparación"),
        (REPARADA, "Reparada"),
        (ENTREGADA, "Entregada"),
        (CANCELADA, "Cancelada"),
    ]
    ETIQUETAS = dict(CHOICES)
    ABIERTOS = [RECIBIDA, EN_EVALUACION, EN_ESPERA_REPUESTO, EN_REPARACION, REPARADA]


class ConfiguracionSistema:
    """Singleton con los parámetros del piloto."""

    _instancia = None
    _candado = Lock()

    def __new__(cls):
        if cls._instancia is None:
            with cls._candado:
                if cls._instancia is None:
                    cls._instancia = super().__new__(cls)
                    cls._instancia._inicializar()
        return cls._instancia

    def _inicializar(self):
        self.nombre_sistema = "ServiceFlow"
        self.prefijo_orden = "RO-"
        self.prefijo_solicitud = "SR-"
        # Transiciones válidas del diagrama de estados (sección 5.1)
        self.transiciones = {
            EstadoOrden.RECIBIDA: {EstadoOrden.EN_EVALUACION, EstadoOrden.CANCELADA},
            EstadoOrden.EN_EVALUACION: {
                EstadoOrden.EN_ESPERA_REPUESTO,
                EstadoOrden.EN_REPARACION,
                EstadoOrden.CANCELADA,
            },
            EstadoOrden.EN_ESPERA_REPUESTO: {EstadoOrden.EN_REPARACION},
            EstadoOrden.EN_REPARACION: {EstadoOrden.REPARADA},
            EstadoOrden.REPARADA: {EstadoOrden.ENTREGADA},
            EstadoOrden.ENTREGADA: set(),
            EstadoOrden.CANCELADA: set(),
        }
        # Pasos que ve el cliente en la barra de avance (Figura 1)
        self.pasos_cliente = ["Recibida", "En evaluación", "En reparación", "Reparada", "Entregada"]
        self.paso_por_estado = {
            EstadoOrden.RECIBIDA: 0,
            EstadoOrden.EN_EVALUACION: 1,
            EstadoOrden.EN_ESPERA_REPUESTO: 1,
            EstadoOrden.EN_REPARACION: 2,
            EstadoOrden.REPARADA: 3,
            EstadoOrden.ENTREGADA: 4,
            EstadoOrden.CANCELADA: 0,
        }
        # Cómo se nombra cada estado para el cliente (lenguaje del mundo real)
        self.estado_cliente = {
            EstadoOrden.RECIBIDA: "Recibida",
            EstadoOrden.EN_EVALUACION: "En evaluación",
            EstadoOrden.EN_ESPERA_REPUESTO: "Esperando un repuesto",
            EstadoOrden.EN_REPARACION: "En reparación",
            EstadoOrden.REPARADA: "Lista para recoger",
            EstadoOrden.ENTREGADA: "Entregada",
            EstadoOrden.CANCELADA: "Cancelada",
        }

    def transicion_valida(self, actual, nuevo):
        return nuevo in self.transiciones.get(actual, set())
