from dataclasses import dataclass


@dataclass
class SubirFotoActivoDTO:
    id_activo: str
    contenido: bytes
    actualizado_por_id: str
    actualizado_por_nombre: str


@dataclass
class EliminarFotoActivoDTO:
    id_activo: str
    actualizado_por_id: str
    actualizado_por_nombre: str
