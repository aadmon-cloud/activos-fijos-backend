from dataclasses import dataclass


@dataclass
class ActualizarCategoriaDTO:
    id_categoria: str
    actualizado_por_id: str
    actualizado_por_nombre: str
    nombre: str | None = None
    descripcion: str | None = None
