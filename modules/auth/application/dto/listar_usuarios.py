from pydantic import BaseModel, Field


class ListarUsuariosInput(BaseModel):
    pagina: int = Field(default=1, ge=1)
    limite: int = Field(default=10, ge=1, le=100)
