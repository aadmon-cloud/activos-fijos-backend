from dataclasses import dataclass


@dataclass
class ActualizarSedeDTO:
    id_sede: str
    actualizado_por_id: str
    actualizado_por_nombre: str
    nombre: str | None = None
    descripcion: str | None = None
