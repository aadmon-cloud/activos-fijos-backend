from dataclasses import dataclass, field

from modules.activos.application.dto.complemento_dto import ComplementoDTO
from modules.activos.domain.entities import TipoActivo


@dataclass
class CrearActivoDTO:
    nombre: str
    numero_inventario: str
    tipo: TipoActivo
    categoria_id: str
    area_id: str
    responsable_id: str
    condicion_id: str
    sede_id: str
    lugar_id: str
    creado_por_id: str
    creado_por_nombre: str
    marca: str | None = None
    modelo: str | None = None
    serie: str | None = None
    descripcion: str | None = None
    complementos: list[ComplementoDTO] = field(default_factory=list)
    observaciones: str | None = None
    foto_url: str | None = None
    ficha_tecnica_url: str | None = None
