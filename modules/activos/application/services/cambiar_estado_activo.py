from dataclasses import replace
from datetime import UTC, datetime

from modules.activos.application.dto.activo_dto import ActivoDTO, activo_a_dto
from modules.activos.application.dto.cambiar_estado_activo_dto import CambiarEstadoActivoDTO
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.ports.historial_activo_repository import (
    HistorialActivoRepositoryPort,
)
from modules.activos.domain.entities import EntradaHistorialActivo
from modules.activos.domain.errors import ActivoNoEncontradoError, TransicionEstadoInvalidaError
from modules.activos.domain.transiciones import es_transicion_valida
from shared.domain.entities.audit import AuditPersona


class CambiarEstadoActivoService:
    def __init__(
        self,
        activo_repository: ActivoRepositoryPort,
        historial_repository: HistorialActivoRepositoryPort,
    ):
        self._activo_repository = activo_repository
        self._historial_repository = historial_repository

    async def ejecutar(self, dto: CambiarEstadoActivoDTO) -> ActivoDTO:
        activo = await self._activo_repository.obtener_por_id(dto.id_activo)
        if activo is None:
            raise ActivoNoEncontradoError(dto.id_activo)

        if not es_transicion_valida(activo.estado_ciclo_vida, dto.estado_nuevo):
            raise TransicionEstadoInvalidaError(
                activo.estado_ciclo_vida.value, dto.estado_nuevo.value
            )

        audit = AuditPersona(
            id_persona=dto.actualizado_por_id,
            nombre=dto.actualizado_por_nombre,
            fecha=datetime.now(UTC),
        )

        await self._historial_repository.registrar(
            EntradaHistorialActivo(
                id=None,
                activo_id=activo.id,
                campo="estado_ciclo_vida",
                valor_anterior=activo.estado_ciclo_vida.value,
                valor_nuevo=dto.estado_nuevo.value,
                modificado_por=audit,
            )
        )

        activo_actualizado = replace(
            activo, estado_ciclo_vida=dto.estado_nuevo, actualizado_por=audit
        )
        activo_guardado = await self._activo_repository.guardar(activo_actualizado)
        return activo_a_dto(activo_guardado)
