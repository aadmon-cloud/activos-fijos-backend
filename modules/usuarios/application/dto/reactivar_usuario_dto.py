from dataclasses import dataclass


@dataclass
class ReactivarUsuarioDTO:
    id_usuario: str
    actualizado_por_id: str
    actualizado_por_nombre: str
