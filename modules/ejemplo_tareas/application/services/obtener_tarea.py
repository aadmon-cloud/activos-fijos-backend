from modules.ejemplo_tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.ejemplo_tareas.domain.entities.tarea import Tarea
from modules.ejemplo_tareas.domain.errors import TareaNoEncontradaError


class ObtenerTareaService:
    def __init__(self, tarea_repository: TareaRepositoryPort):
        self._tarea_repository = tarea_repository

    async def ejecutar(self, tarea_id: str) -> Tarea:
        """Raises:
            TareaNoEncontradaError: Si el identificador no existe.
        """
        tarea = await self._tarea_repository.obtener_por_id(tarea_id)
        if not tarea:
            raise TareaNoEncontradaError(tarea_id)
        return tarea
