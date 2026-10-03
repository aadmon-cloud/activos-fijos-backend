from abc import ABC, abstractmethod

from modules.solicitudes.domain.entities import EstadoSolicitud, Solicitud, TipoSolicitud


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
        skip: int,
        limit: int,
    ) -> list[Solicitud]: ...
