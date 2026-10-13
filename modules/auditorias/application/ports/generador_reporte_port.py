from abc import ABC, abstractmethod

from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditado
from modules.auditorias.domain.entities import Auditoria


class GeneradorReportePort(ABC):
    @abstractmethod
    async def generar_pdf(self, auditoria: Auditoria, usuario: UsuarioAuditado) -> bytes: ...
