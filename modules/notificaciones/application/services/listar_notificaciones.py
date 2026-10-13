from modules.notificaciones.application.dto.notificacion_dto import (
    ListadoNotificacionesDTO,
    notificacion_a_dto,
)
from modules.notificaciones.application.ports.notificacion_repository import (
    NotificacionRepositoryPort,
)
from modules.notificaciones.domain.entities import EstadoNotificacion

_LIMITE_MAXIMO = 1000


class ListarNotificacionesService:
    def __init__(self, notificacion_repository: NotificacionRepositoryPort):
        self._notificacion_repository = notificacion_repository

    async def ejecutar(
        self, estado: EstadoNotificacion | None, skip: int, limit: int
    ) -> ListadoNotificacionesDTO:
        limit = min(limit, _LIMITE_MAXIMO)
        notificaciones = await self._notificacion_repository.listar(estado, skip, limit)
        total = await self._notificacion_repository.contar(estado)

        return ListadoNotificacionesDTO(
            items=[notificacion_a_dto(n) for n in notificaciones],
            total=total,
            skip=skip,
            limit=limit,
        )
