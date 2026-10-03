from dataclasses import dataclass
from datetime import datetime


@dataclass
class TareaDTO:
    id: str
    titulo: str
    completada: bool
    fecha_creacion: datetime
