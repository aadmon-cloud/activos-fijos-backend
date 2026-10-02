from modules.ejemplo_tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.ejemplo_tareas.domain.entities.tarea import Tarea
from modules.ejemplo_tareas.domain.errors import TareaNoEncontradaError


class CompletarTareaService:
    def __init__(self, tarea_repository: TareaRepositoryPort):
        self._tarea_repository = tarea_repository

    async def ejecutar(self, tarea_id: str) -> Tarea:
        """Marca como completada una tarea existente.

        Raises:
            TareaNoEncontradaError: Si la tarea no existe.
        """
        tarea = await self._tarea_repository.obtener_por_id(tarea_id)
        if not tarea:
            raise TareaNoEncontradaError(tarea_id)

        tarea_completada = tarea.completar()
        return await self._tarea_repository.actualizar(tarea_completada)
