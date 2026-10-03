from pydantic import BaseModel, Field

from modules.catalogos.domain.entities import TipoLugar

_PATRON_COLOR_HEX = r"^#[0-9A-Fa-f]{6}$"


class CrearAreaRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None


class ActualizarAreaRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None


class AreaResponse(BaseModel):
    id: str
    nombre: str
    descripcion: str | None


class CrearCategoriaRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None


class ActualizarCategoriaRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None


class CategoriaResponse(BaseModel):
    id: str
    nombre: str
    descripcion: str | None


class CrearCondicionRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    color: str = Field(pattern=_PATRON_COLOR_HEX)
    descripcion: str | None = None


class ActualizarCondicionRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    color: str | None = Field(default=None, pattern=_PATRON_COLOR_HEX)
    descripcion: str | None = None


class CondicionResponse(BaseModel):
    id: str
    nombre: str
    color: str
    descripcion: str | None


class CrearSedeRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    descripcion: str | None = None


class ActualizarSedeRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    descripcion: str | None = None


class SedeResponse(BaseModel):
    id: str
    nombre: str
    descripcion: str | None


class CrearLugarRequest(BaseModel):
    nombre: str = Field(min_length=1, max_length=200)
    tipo: TipoLugar
    sede_id: str


class ActualizarLugarRequest(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    tipo: TipoLugar | None = None


class LugarResponse(BaseModel):
    id: str
    nombre: str
    tipo: str
    sede_id: str
