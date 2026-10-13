from dataclasses import dataclass

from modules.activos.application.dto.complemento_dto import ComplementoDTO


@dataclass
class ActualizarActivoDTO:
    id_activo: str
    actualizado_por_id: str
    actualizado_por_nombre: str
    nombre: str | None = None
    marca: str | None = None
    modelo: str | None = None
    serie: str | None = None
    descripcion: str | None = None
    categoria_id: str | None = None
    area_id: str | None = None
    responsable_id: str | None = None
    condicion_id: str | None = None
    sede_id: str | None = None
    lugar_id: str | None = None
    complementos: list[ComplementoDTO] | None = None
    observaciones: str | None = None
    foto_url: str | None = None
    ficha_tecnica_url: str | None = None
