from dataclasses import dataclass
from datetime import datetime

from modules.activos.application.dto.complemento_dto import ComplementoDTO, complemento_a_dto
from modules.activos.domain.entities import Activo


@dataclass
class ActivoDTO:
    id: str
    nombre: str
    numero_inventario: str
    tipo: str
    marca: str | None
    modelo: str | None
    serie: str | None
    descripcion: str | None
    categoria_id: str
    area_id: str
    responsable_id: str
    condicion_id: str
    estado_ciclo_vida: str
    sede_id: str
    lugar_id: str
    fecha_ingreso: datetime
    complementos: list[ComplementoDTO]
    observaciones: str | None
    foto_url: str | None
    ficha_tecnica_url: str | None


def activo_a_dto(activo: Activo) -> ActivoDTO:
    return ActivoDTO(
        id=activo.id,
        nombre=activo.nombre,
        numero_inventario=activo.numero_inventario,
        tipo=activo.tipo.value,
        marca=activo.marca,
        modelo=activo.modelo,
        serie=activo.serie,
        descripcion=activo.descripcion,
        categoria_id=activo.categoria_id,
        area_id=activo.area_id,
        responsable_id=activo.responsable_id,
        condicion_id=activo.condicion_id,
        estado_ciclo_vida=activo.estado_ciclo_vida.value,
        sede_id=activo.sede_id,
        lugar_id=activo.lugar_id,
        fecha_ingreso=activo.creado_por.fecha,
        complementos=[complemento_a_dto(c) for c in activo.complementos],
        observaciones=activo.observaciones,
        foto_url=activo.foto_url,
        ficha_tecnica_url=activo.ficha_tecnica_url,
    )
