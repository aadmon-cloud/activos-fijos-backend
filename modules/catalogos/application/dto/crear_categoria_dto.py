from dataclasses import dataclass


@dataclass
class CrearCategoriaDTO:
    nombre: str
    creado_por_id: str
    creado_por_nombre: str
    descripcion: str | None = None
