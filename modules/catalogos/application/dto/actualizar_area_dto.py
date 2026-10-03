from dataclasses import dataclass


@dataclass
class ActualizarAreaDTO:
    id_area: str
    actualizado_por_id: str
    actualizado_por_nombre: str
    nombre: str | None = None
    descripcion: str | None = None
