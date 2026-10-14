from dataclasses import dataclass

from modules.movimientos.domain.entities import ResultadoChequeo


@dataclass
class ChequearItemDTO:
    id_movimiento: str
    activo_id: str
    resultado: ResultadoChequeo
    actor_id: str
    actor_nombre: str
    actor_rol: str
    observacion: str | None = None


@dataclass
class AceptarActaDTO:
    id_movimiento: str
    acta_id: str
    actor_id: str
    actor_nombre: str
    actor_correo: str


@dataclass
class ObtenerActaDTO:
    id_movimiento: str
    acta_id: str
    actor_id: str
    actor_rol: str
