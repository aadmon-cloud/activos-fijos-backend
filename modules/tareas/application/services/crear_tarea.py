from datetime import UTC, datetime

from modules.tareas.application.dto.crear_tarea_dto import CrearTareaDTO
from modules.tareas.application.dto.tarea_dto import TareaDTO
from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.tareas.domain.entities import Tarea
from modules.tareas.domain.errors import TituloTareaVacioError


class CrearTareaService:
    def __init__(self, tarea_repository: TareaRepositoryPort):
        self._tarea_repository = tarea_repository

    async def ejecutar(self, dto: CrearTareaDTO) -> TareaDTO:
        titulo = dto.titulo.strip()
        if not titulo:
            raise TituloTareaVacioError()

        tarea = Tarea(
            id=None,
            titulo=titulo,
            completada=False,
            fecha_creacion=datetime.now(UTC),
        )
        tarea_guardada = await self._tarea_repository.guardar(tarea)

        return TareaDTO(
            id=tarea_guardada.id,
            titulo=tarea_guardada.titulo,
            completada=tarea_guardada.completada,
            fecha_creacion=tarea_guardada.fecha_creacion,
        )
