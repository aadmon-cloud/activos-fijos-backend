from dataclasses import replace
from datetime import UTC, datetime

from modules.mantenimientos.application.dto.cambiar_estado_mantenimiento_dto import (
    CambiarEstadoMantenimientoDTO,
)
from modules.mantenimientos.application.dto.mantenimiento_dto import (
    MantenimientoDTO,
    mantenimiento_a_dto,
)
from modules.mantenimientos.application.ports.mantenimiento_repository import (
    MantenimientoRepositoryPort,
)
from modules.mantenimientos.application.ports.solicitud_estado_port import (
    ActorSolicitud,
    SolicitudEstadoPort,
)
from modules.mantenimientos.domain.entities import EstadoMantenimiento
from modules.mantenimientos.domain.errors import (
    MantenimientoNoEncontradoError,
    TransicionEstadoMantenimientoInvalidaError,
)
from modules.mantenimientos.domain.transiciones import es_transicion_valida
from shared.domain.entities.audit import AuditPersona


class CambiarEstadoMantenimientoService:
    def __init__(
        self,
        mantenimiento_repository: MantenimientoRepositoryPort,
        solicitud_estado: SolicitudEstadoPort,
    ):
        self._mantenimiento_repository = mantenimiento_repository
        self._solicitud_estado = solicitud_estado

    async def ejecutar(self, dto: CambiarEstadoMantenimientoDTO) -> MantenimientoDTO:
        mantenimiento = await self._mantenimiento_repository.obtener_por_id(dto.id_mantenimiento)
        if mantenimiento is None:
            raise MantenimientoNoEncontradoError(dto.id_mantenimiento)

        if not es_transicion_valida(mantenimiento.estado, dto.estado_nuevo):
            raise TransicionEstadoMantenimientoInvalidaError(
                mantenimiento.estado.value, dto.estado_nuevo.value
            )

        mantenimiento_actualizado = replace(
            mantenimiento,
            estado=dto.estado_nuevo,
            actualizado_por=AuditPersona(
                id_persona=dto.actor_id, nombre=dto.actor_nombre, fecha=datetime.now(UTC)
            ),
        )

        mantenimiento_guardado = await self._mantenimiento_repository.guardar(
            mantenimiento_actualizado
        )

        if (
            dto.estado_nuevo == EstadoMantenimiento.COMPLETADO
            and mantenimiento.solicitud_id is not None
        ):
            await self._solicitud_estado.marcar_resuelta(
                mantenimiento.solicitud_id,
                ActorSolicitud(
                    id=dto.actor_id,
                    nombre=dto.actor_nombre,
                    rol=dto.actor_rol,
                    area_id=dto.actor_area_id,
                ),
            )

        return mantenimiento_a_dto(mantenimiento_guardado)
