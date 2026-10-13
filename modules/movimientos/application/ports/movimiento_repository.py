from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from modules.movimientos.domain.entities import EstadoMovimiento, Movimiento, TipoMovimiento


@dataclass(frozen=True)
class VisibilidadMovimiento:
    """Restringe el listado a lo que ese usuario puede ver: lo que creo, donde es destinatario o responsable
    original de algun activo, y los movimientos de los activos que tiene a su cargo."""

    actor_id: str
    activo_ids: frozenset[str]


@dataclass(frozen=True)
class ParaMiMovimiento:
    """Movimientos que le conciernen al usuario como responsable o destinatario (no solo como quien los creo).

    Al administrador ademas le concierne lo que espera una accion suya (aprobar una baja, confirmar una salida
    o recibir una devolucion)."""

    actor_id: str
    activo_ids: frozenset[str]
    es_administrador: bool


class MovimientoRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, movimiento: Movimiento) -> Movimiento: ...

    @abstractmethod
    async def obtener_por_id(self, id_movimiento: str) -> Movimiento | None: ...

    @abstractmethod
    async def activos_ocupados(self, activo_ids: list[str]) -> set[str]:
        """De estos activos, los que ya estan en otro movimiento sin terminar (pendiente, en curso o por devolver)."""

    @abstractmethod
    async def listar_devoluciones_por_recordar(self, limite_fecha: datetime) -> list[Movimiento]:
        """Movimientos en curso con devolucion estimada hasta `limite_fecha` y sin recordatorio."""

    @abstractmethod
    async def listar(
        self,
        tipo: TipoMovimiento | None,
        estado: EstadoMovimiento | None,
        activo_id: str | None,
        usuario_destino_id: str | None,
        creado_por_id: str | None,
        visible_para: VisibilidadMovimiento | None,
        para_mi: ParaMiMovimiento | None,
        skip: int,
        limit: int,
    ) -> list[Movimiento]: ...

    @abstractmethod
    async def contar(
        self,
        tipo: TipoMovimiento | None,
        estado: EstadoMovimiento | None,
        activo_id: str | None,
        usuario_destino_id: str | None,
        creado_por_id: str | None,
        visible_para: VisibilidadMovimiento | None,
        para_mi: ParaMiMovimiento | None,
    ) -> int: ...
