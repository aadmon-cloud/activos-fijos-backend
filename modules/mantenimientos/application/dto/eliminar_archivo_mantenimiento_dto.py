from dataclasses import dataclass


@dataclass
class EliminarArchivoMantenimientoDTO:
    id_mantenimiento: str
    archivo_id: str
    actualizado_por_id: str
    actualizado_por_nombre: str
