from dataclasses import dataclass
from datetime import datetime

from modules.auditorias.application.dto.item_auditoria_dto import ItemAuditoriaDTO, item_a_dto
from modules.auditorias.domain.entities import Auditoria, EstadoAuditoria, ResultadoVerificacion


@dataclass
class AuditoriaDTO:
    id: str
    usuario_auditado_id: str
    estado: EstadoAuditoria
    items: list[ItemAuditoriaDTO]
    fecha_inicio: datetime
    fecha_cierre: datetime | None
    pdf_archivo_id: str | None
    detalle_error_notificacion: str | None
    auditor_id: str
    auditor_nombre: str
    total: int
    encontrados: int
    encontrados_con_novedad: int
    no_encontrados: int
    pendientes: int


def auditoria_a_dto(auditoria: Auditoria) -> AuditoriaDTO:
    items = [item_a_dto(i) for i in auditoria.items]
    return AuditoriaDTO(
        id=auditoria.id,
        usuario_auditado_id=auditoria.usuario_auditado_id,
        estado=auditoria.estado,
        items=items,
        fecha_inicio=auditoria.creado_por.fecha,
        fecha_cierre=auditoria.fecha_cierre,
        pdf_archivo_id=auditoria.pdf_archivo_id,
        detalle_error_notificacion=auditoria.detalle_error_notificacion,
        auditor_id=auditoria.creado_por.id_persona,
        auditor_nombre=auditoria.creado_por.nombre,
        total=len(auditoria.items),
        encontrados=sum(
            1 for i in auditoria.items if i.resultado == ResultadoVerificacion.ENCONTRADO
        ),
        encontrados_con_novedad=sum(
            1
            for i in auditoria.items
            if i.resultado == ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD
        ),
        no_encontrados=sum(
            1 for i in auditoria.items if i.resultado == ResultadoVerificacion.NO_ENCONTRADO
        ),
        pendientes=sum(1 for i in auditoria.items if i.resultado is None),
    )
