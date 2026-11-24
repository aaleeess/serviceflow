"""DTO de coordinación (sección 4.9.1)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class SolicitudPendienteDTO:
    """Lo que el coordinador necesita para decidir (CU-11, Figura 3)."""

    codigo: str
    tipo: str
    tipo_texto: str
    solicitante: str
    creada: datetime
    cantidad: int
    repuesto: str
    codigo_pieza: str
    orden: str
    necesita: int
    destino: str
    destino_disponible: int
    origen: str
    origen_disponible: int
    origen_queda: int


@dataclass(frozen=True)
class SolicitudAutorizadaDTO:
    codigo: str
    tipo: str
    tipo_texto: str
    cantidad: int
    repuesto: str
    orden: str
    origen: str
    revisor: str
    resuelta: datetime | None
