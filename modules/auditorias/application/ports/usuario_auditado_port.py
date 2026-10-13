from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class UsuarioAuditado:
    id: str
    nombre_completo: str
    identificacion: str | None
    email: str
    activo: bool


class UsuarioAuditadoPort(ABC):
    """Tambien se usa para resolver el correo del auditor (es un usuario como cualquier otro),
    no solo el del usuario auditado."""

    @abstractmethod
    async def obtener(self, usuario_id: str) -> UsuarioAuditado | None: ...
