"""DTO de órdenes (sección 4.9.1): solo los datos que cada pantalla puede mostrar."""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class PasoDTO:
    nombre: str
    situacion: str  # "hecho", "actual" o "pendiente"


@dataclass(frozen=True)
class EventoDTO:
    descripcion: str
    fecha: datetime


@dataclass(frozen=True)
class SeguimientoDTO:
    """Lo que el cliente ve de su orden (CU-04, Figura 1).

    Incluye el diagnóstico técnico (qué tiene el equipo y qué pieza necesita), pero no el
    nombre del técnico, el stock, las reservas ni datos de otros clientes.
    """

    codigo: str
    modelo_equipo: str
    falla_reportada: str
    centro: str
    diagnostico: str
    pieza: str
    estado: str
    estado_texto: str
    pasos: list
    fecha_estimada: date | None
    historial: list
    puede_cancelar: bool
    esperando_repuesto: bool
    cancelada: bool


@dataclass(frozen=True)
class SolicitudDTO:
    """Respuesta al registrar una solicitud (CU-02, Figura 5)."""

    codigo: str
    estado_texto: str


@dataclass(frozen=True)
class OrdenTecnicoDTO:
    codigo: str
    modelo_equipo: str
    falla_reportada: str
    cliente: str
    estado: str
    estado_texto: str
    fecha_estimada: date | None
    siguiente: str  # diagnosticar, almacen, confirmar_fecha, marcar_reparada, entregar, ninguno
    repuesto: str = ""
    diagnostico: str = ""


@dataclass(frozen=True)
class OpcionRepuestoDTO:
    id: int
    nombre: str
    disponible: int


@dataclass
class BandejaTecnicoDTO:
    ordenes: list
    conteos: dict
    filtro: str
    seleccionada: OrdenTecnicoDTO | None = None
    repuestos: list = field(default_factory=list)
