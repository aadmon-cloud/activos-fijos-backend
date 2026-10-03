from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class Tarea:
    id: str | None
    titulo: str
    completada: bool
    fecha_creacion: datetime
