from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class AuditPersona:
    id_persona: str
    nombre: str
    fecha: datetime
