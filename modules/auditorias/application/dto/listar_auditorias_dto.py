from dataclasses import dataclass

from modules.auditorias.domain.entities import EstadoAuditoria


@dataclass
class ListarAuditoriasDTO:
    usuario_auditado_id: str | None = None
    estado: EstadoAuditoria | None = None
    creado_por_id: str | None = None
    skip: int = 0
    limit: int = 100
