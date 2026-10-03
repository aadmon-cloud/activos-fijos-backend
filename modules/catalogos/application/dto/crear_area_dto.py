from dataclasses import dataclass


@dataclass
class CrearAreaDTO:
    nombre: str
    creado_por_id: str
    creado_por_nombre: str
    descripcion: str | None = None
