from pydantic import BaseModel

from modules.auth.domain.entities.usuario import Usuario


class ResultadoLoginDTO(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: Usuario
