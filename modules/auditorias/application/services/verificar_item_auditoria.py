from dataclasses import replace
from datetime import UTC, datetime

from modules.auditorias.application.dto.auditoria_dto import AuditoriaDTO, auditoria_a_dto
from modules.auditorias.application.dto.verificar_item_auditoria_dto import (
    VerificarItemAuditoriaDTO,
)
from modules.auditorias.application.ports.auditoria_repository import AuditoriaRepositoryPort
from modules.auditorias.domain.entities import EstadoAuditoria, ResultadoVerificacion
from modules.auditorias.domain.errors import (
    AuditoriaNoEncontradaError,
    AuditoriaNoModificableError,
    ItemAuditoriaNoEncontradoError,
    ObservacionObligatoriaError,
)


class VerificarItemAuditoriaService:
    def __init__(self, auditoria_repository: AuditoriaRepositoryPort):
        self._auditoria_repository = auditoria_repository

    async def ejecutar(self, dto: VerificarItemAuditoriaDTO) -> AuditoriaDTO:
        auditoria = await self._auditoria_repository.obtener_por_id(dto.id_auditoria)
        if auditoria is None:
            raise AuditoriaNoEncontradaError(dto.id_auditoria)

        if auditoria.estado != EstadoAuditoria.EN_PROGRESO:
            raise AuditoriaNoModificableError(dto.id_auditoria)

        if not any(item.activo_id == dto.activo_id for item in auditoria.items):
            raise ItemAuditoriaNoEncontradoError(dto.activo_id)

        if dto.resultado == ResultadoVerificacion.ENCONTRADO_CON_NOVEDAD and not (
            dto.observacion and dto.observacion.strip()
        ):
            raise ObservacionObligatoriaError()

        # Sin espacios sobrantes; una observacion vacia no se guarda.
        observacion = (dto.observacion or "").strip() or None
        ahora = datetime.now(UTC)
        items_actualizados = [
            (
                replace(item, resultado=dto.resultado, observacion=observacion, verificado_en=ahora)
                if item.activo_id == dto.activo_id
                else item
            )
            for item in auditoria.items
        ]

        auditoria_actualizada = replace(auditoria, items=items_actualizados)
        auditoria_guardada = await self._auditoria_repository.guardar(auditoria_actualizada)
        return auditoria_a_dto(auditoria_guardada)
