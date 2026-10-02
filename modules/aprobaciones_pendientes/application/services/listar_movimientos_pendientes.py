from shared.application.dto.pagination import RespuestaPaginada

from modules.aprobaciones_pendientes.application.dto.listar_movimientos_pendientes import (
    ListarMovimientosPendientesInput,
)
from modules.aprobaciones_pendientes.application.ports.movimiento_pendiente_repository import (
    MovimientoPendienteRepositoryPort,
)
from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    MovimientoPendiente,
)


class ListarMovimientosPendientesService:
    def __init__(self, movimiento_pendiente_repository: MovimientoPendienteRepositoryPort):
        self._movimiento_pendiente_repository = movimiento_pendiente_repository

    async def ejecutar(
        self,
        entrada: ListarMovimientosPendientesInput,
        usuario_actual_id: str,
        es_super_admin: bool,
    ) -> RespuestaPaginada[MovimientoPendiente]:
        """`super_admin` ve las propuestas de todos los usuarios; cualquier
        otro rol solo ve las propias — el filtro de dueño se fuerza acá, no
        se confía en lo que venga del request HTTP."""
        filtro = entrada.model_copy(
            update={"creado_por_id": None if es_super_admin else usuario_actual_id}
        )
        pendientes, total = await self._movimiento_pendiente_repository.listar(filtro)
        return RespuestaPaginada.crear(
            items=pendientes, page=entrada.pagina, limit=entrada.limite, total=total
        )
