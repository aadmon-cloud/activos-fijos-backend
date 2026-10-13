from dataclasses import dataclass


@dataclass
class IniciarAuditoriaDTO:
    usuario_auditado_id: str
    auditor_id: str
    auditor_nombre: str
