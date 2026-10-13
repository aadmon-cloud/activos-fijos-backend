from abc import ABC, abstractmethod
from dataclasses import dataclass

from modules.solicitudes.domain.entities import EstadoSolicitud, Solicitud, TipoSolicitud


@dataclass(frozen=True)
class VisibilidadSolicitud:
    """Restringe el listado a lo que ese usuario puede ver: lo que creo y lo asignado a su rol o area."""

    actor_id: str
    rol: str
    area_id: str | None


class SolicitudRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, solicitud: Solicitud) -> Solicitud: ...

    @abstractmethod
    async def obtener_por_id(self, id_solicitud: str) -> Solicitud | None: ...

    @abstractmethod
    async def listar(
        self,
        tipo: TipoSolicitud | None,
        estado: EstadoSolicitud | None,
        activo_id: str | None,
        rol_asignado: str | None,
        area_id: str | None,
        creado_por_id: str | None,
        visible_para: VisibilidadSolicitud | None,
        skip: int,
        limit: int,
    ) -> list[Solicitud]: ...

    @abstractmethod
    async def contar(
        self,
        tipo: TipoSolicitud | None,
        estado: EstadoSolicitud | None,
        activo_id: str | None,
        rol_asignado: str | None,
        area_id: str | None,
        creado_por_id: str | None,
        visible_para: VisibilidadSolicitud | None,
    ) -> int: ...
