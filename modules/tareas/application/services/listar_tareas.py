from modules.tareas.application.dto.tarea_dto import TareaDTO
from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort


class ListarTareasService:
    def __init__(self, tarea_repository: TareaRepositoryPort):
        self._tarea_repository = tarea_repository

    async def ejecutar(self) -> list[TareaDTO]:
        tareas = await self._tarea_repository.listar()
        return [
            TareaDTO(
                id=tarea.id,
                titulo=tarea.titulo,
                completada=tarea.completada,
                fecha_creacion=tarea.fecha_creacion,
            )
            for tarea in tareas
        ]
