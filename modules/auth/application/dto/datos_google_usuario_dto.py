from pydantic import BaseModel


class DatosGoogleUsuarioDTO(BaseModel):
    email: str
    google_id: str
    nombre: str
    picture: str | None = None
