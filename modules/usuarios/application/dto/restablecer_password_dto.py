from dataclasses import dataclass


@dataclass
class RestablecerPasswordDTO:
    id_usuario: str
    password_nueva: str
    actualizado_por_id: str
    actualizado_por_nombre: str
