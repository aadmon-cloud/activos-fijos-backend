from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ActivoResumenMovimiento:
    id: str
    responsable_id: str
    estado_ciclo_vida: str
    nombre: str = ""
    numero_inventario: str = ""


class ActivoMovimientoPort(ABC):
    """Lee y escribe sobre el activo reutilizando los servicios reales de modules.activos
    (mismo patron que ActivoEstadoAdapter de solicitudes), para que el historial de activos y su
    matriz de transiciones tengan una sola implementacion."""

    @abstractmethod
    async def obtener_resumen(self, activo_id: str) -> ActivoResumenMovimiento | None: ...

    @abstractmethod
    async def obtener_resumenes(self, activo_ids: list[str]) -> dict[str, ActivoResumenMovimiento]:
        """Resumen de cada activo que exista; un id ausente en el resultado ya no existe."""

    @abstractmethod
    async def listar_ids_por_responsable(self, responsable_id: str) -> list[str]:
        """Ids de los activos que el usuario tiene a su cargo."""

    @abstractmethod
    async def cambiar_responsable(
        self, activo_id: str, responsable_nuevo_id: str, actor_id: str, actor_nombre: str
    ) -> bool: ...

    @abstractmethod
    async def cambiar_estado(
        self, activo_id: str, estado_nuevo: str, actor_id: str, actor_nombre: str
    ) -> bool: ...

    @abstractmethod
    async def registrar_nota(
        self, activo_id: str, nota: str, movimiento_id: str, actor_id: str, actor_nombre: str
    ) -> None:
        """Deja una novedad en el historial del activo (p. ej. el hallazgo al recibirlo de vuelta)."""
