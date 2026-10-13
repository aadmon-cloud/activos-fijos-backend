from dataclasses import dataclass


@dataclass
class CambiarPasswordDTO:
    id_usuario: str
    password_actual: str
    password_nueva: str
