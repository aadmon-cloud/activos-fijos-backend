from dataclasses import dataclass


@dataclass
class CrearCondicionDTO:
    nombre: str
    color: str
    creado_por_id: str
    creado_por_nombre: str
    descripcion: str | None = None
