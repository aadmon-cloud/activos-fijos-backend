from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from modules.mantenimientos.application.dto.archivo_mantenimiento_dto import (
    ArchivoMantenimientoDTO,
    archivo_a_dto,
)
from modules.mantenimientos.domain.entities import Mantenimiento


@dataclass
class MantenimientoDTO:
    id: str
    activo_id: str
    solicitud_id: str | None
    tipo: str
    tecnico_responsable_id: str
    fecha: datetime
    observaciones: str | None
    costo: Decimal | None
    documentos: list[ArchivoMantenimientoDTO]
    evidencias: list[ArchivoMantenimientoDTO]
    estado: str
    frecuencia_dias: int | None
    proxima_fecha_sugerida: datetime | None
    alerta_enviada: bool
    creado_por_id: str
    creado_por_nombre: str
    fecha_creacion: datetime


def mantenimiento_a_dto(mantenimiento: Mantenimiento) -> MantenimientoDTO:
    return MantenimientoDTO(
        id=mantenimiento.id,
        activo_id=mantenimiento.activo_id,
        solicitud_id=mantenimiento.solicitud_id,
        tipo=mantenimiento.tipo.value,
        tecnico_responsable_id=mantenimiento.tecnico_responsable_id,
        fecha=mantenimiento.fecha,
        observaciones=mantenimiento.observaciones,
        costo=mantenimiento.costo,
        documentos=[archivo_a_dto(a) for a in mantenimiento.documentos],
        evidencias=[archivo_a_dto(a) for a in mantenimiento.evidencias],
        estado=mantenimiento.estado.value,
        frecuencia_dias=mantenimiento.frecuencia_dias,
        proxima_fecha_sugerida=mantenimiento.proxima_fecha_sugerida,
        alerta_enviada=mantenimiento.alerta_enviada,
        creado_por_id=mantenimiento.creado_por.id_persona,
        creado_por_nombre=mantenimiento.creado_por.nombre,
        fecha_creacion=mantenimiento.creado_por.fecha,
    )
