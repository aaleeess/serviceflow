"""DTO de inventario (sección 4.9.1)."""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class StockDTO:
    inventario_id: int
    repuesto: str
    codigo_pieza: str
    fisico: int
    reservado: int
    disponible: int


@dataclass(frozen=True)
class ResultadoReservaDTO:
    """Respuesta a 'Reservar repuesto' (CU-08, Figura 2)."""

    exito: bool
    mensaje: str
    faltante: int = 0
    ofrecer_reposicion: bool = False


@dataclass(frozen=True)
class FilaReservaDTO:
    orden: str
    modelo_equipo: str
    desde: datetime
    fecha_estimada: date | None
    repuesto: str
    codigo_pieza: str
    necesita: int
    disponible: int
    situacion: str  # falta, lista, solicitada, autorizada, reservada
    faltante: int


@dataclass(frozen=True)
class DisponibilidadCentroDTO:
    centro_id: int
    centro: str
    disponible: int
    es_este: bool
    alcanza: bool


@dataclass(frozen=True)
class OpcionesFaltanteDTO:
    orden: str
    repuesto: str
    faltante: int
    por_centro: list
    solicitud: str = ""  # texto si ya hay una solicitud en curso


@dataclass
class PanelReservasDTO:
    filas: list
    resumen: dict
    filtro: str
    busqueda: str
    opciones: OpcionesFaltanteDTO | None = None
    agotados: list = field(default_factory=list)


@dataclass(frozen=True)
class MovimientoDTO:
    fecha: datetime
    tipo: str
    repuesto: str
    cantidad: int
    motivo: str
    referencia: str
    usuario: str
