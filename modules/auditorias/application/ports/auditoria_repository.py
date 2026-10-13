from abc import ABC, abstractmethod

from modules.auditorias.domain.entities import Auditoria, EstadoAuditoria


class AuditoriaRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, auditoria: Auditoria) -> Auditoria: ...

    @abstractmethod
    async def obtener_por_id(self, id_auditoria: str) -> Auditoria | None: ...

    @abstractmethod
    async def listar(
        self,
        usuario_auditado_id: str | None,
        estado: EstadoAuditoria | None,
        creado_por_id: str | None,
        skip: int,
        limit: int,
    ) -> list[Auditoria]: ...

    @abstractmethod
    async def contar(
        self,
        usuario_auditado_id: str | None,
        estado: EstadoAuditoria | None,
        creado_por_id: str | None,
    ) -> int: ...
