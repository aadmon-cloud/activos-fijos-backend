from datetime import datetime

from pydantic import BaseModel, Field


class ActualizarPermisosRolRequest(BaseModel):
    # El maximo evita cuerpos enormes: el catalogo tiene unas 25 funciones.
    permisos: list[str] = Field(max_length=100)


class FuncionResponse(BaseModel):
    clave: str
    modulo: str
    etiqueta: str
    descripcion: str
    es_base: bool


class RolMatrizResponse(BaseModel):
    rol: str
    etiqueta: str
    editable: bool
    permisos: list[str]


class MatrizResponse(BaseModel):
    funciones: list[FuncionResponse]
    roles: list[RolMatrizResponse]


class CambioPermisoResponse(BaseModel):
    id: str | None
    rol: str
    permiso: str
    accion: str
    por_id: str
    por_nombre: str
    fecha: datetime
