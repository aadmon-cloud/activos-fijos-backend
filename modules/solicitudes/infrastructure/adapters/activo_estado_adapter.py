from modules.activos.application.dto.cambiar_estado_activo_dto import CambiarEstadoActivoDTO
from modules.activos.application.ports.activo_repository import ActivoRepositoryPort
from modules.activos.application.services.cambiar_estado_activo import CambiarEstadoActivoService
from modules.activos.domain.entities import EstadoCicloVida
from modules.activos.domain.errors import ActivoNoEncontradoError, TransicionEstadoInvalidaError
from modules.solicitudes.application.ports.activo_estado_port import ActivoEstadoPort

# Unico archivo de solicitudes que usa codigo del modulo activos. Aqui se reutiliza su servicio de
# cambio de estado a proposito: asi la matriz de transiciones y el registro en el historial del activo
# tienen una sola implementacion, en vez de repetirlas escribiendo en su coleccion.


class ActivoEstadoAdapter(ActivoEstadoPort):
    def __init__(
        self,
        activo_repository: ActivoRepositoryPort,
        cambiar_estado_service: CambiarEstadoActivoService,
    ):
        self._activo_repository = activo_repository
        self._cambiar_estado_service = cambiar_estado_service

    async def obtener_estado(self, activo_id: str) -> str | None:
        activo = await self._activo_repository.obtener_por_id(activo_id)

        return activo.estado_ciclo_vida.value if activo else None

    async def cambiar_estado(
        self, activo_id: str, estado_nuevo: str, actor_id: str, actor_nombre: str
    ) -> bool:
        try:
            await self._cambiar_estado_service.ejecutar(
                CambiarEstadoActivoDTO(
                    id_activo=activo_id,
                    estado_nuevo=EstadoCicloVida(estado_nuevo),
                    actualizado_por_id=actor_id,
                    actualizado_por_nombre=actor_nombre,
                )
            )
        except (ActivoNoEncontradoError, TransicionEstadoInvalidaError):
            return False

        return True
