from dataclasses import dataclass

from modules.catalogos.domain.entities import TipoLugar


@dataclass
class ActualizarLugarDTO:
    id_lugar: str
    actualizado_por_id: str
    actualizado_por_nombre: str
    nombre: str | None = None
    tipo: TipoLugar | None = None
