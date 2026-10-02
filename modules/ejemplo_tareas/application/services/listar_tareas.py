from shared.application.dto.pagination import RespuestaPaginada

from modules.ejemplo_tareas.application.dto.listar_tareas import ListarTareasInput
from modules.ejemplo_tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.ejemplo_tareas.domain.entities.tarea import Tarea


class ListarTareasService:
    def __init__(self, tarea_repository: TareaRepositoryPort):
        self._tarea_repository = tarea_repository

    async def ejecutar(self, entrada: ListarTareasInput) -> RespuestaPaginada[Tarea]:
        tareas, total = await self._tarea_repository.listar_paginado(
            pagina=entrada.pagina,
            limite=entrada.limite,
        )
        return RespuestaPaginada.crear(
            items=tareas,
            page=entrada.pagina,
            limit=entrada.limite,
            total=total,
        )
