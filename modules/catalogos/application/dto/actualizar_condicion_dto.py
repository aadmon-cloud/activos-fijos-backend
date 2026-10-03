from dataclasses import dataclass


@dataclass
class ActualizarCondicionDTO:
    id_condicion: str
    actualizado_por_id: str
    actualizado_por_nombre: str
    nombre: str | None = None
    color: str | None = None
    descripcion: str | None = None
