from dataclasses import dataclass


@dataclass
class CerrarAuditoriaDTO:
    id_auditoria: str
    actor_id: str
    actor_nombre: str
