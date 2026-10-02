from modules.ejemplo_tareas.application.dto.crear_tarea import CrearTareaInput
from modules.ejemplo_tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.ejemplo_tareas.domain.entities.tarea import Tarea


class CrearTareaService:
    def __init__(self, tarea_repository: TareaRepositoryPort):
        self._tarea_repository = tarea_repository

    async def ejecutar(self, entrada: CrearTareaInput) -> Tarea:
        tarea = Tarea.crear(
            titulo=entrada.titulo,
            descripcion=entrada.descripcion,
        )
        return await self._tarea_repository.guardar(tarea)
