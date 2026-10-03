from dataclasses import dataclass

from modules.usuarios.application.dto.usuario_dto import UsuarioDTO


@dataclass
class TokenDTO:
    access_token: str
    token_type: str
    usuario: UsuarioDTO
