from dataclasses import dataclass


@dataclass(frozen=True)
class FuncionDTO:
    clave: str
    modulo: str
    etiqueta: str
    descripcion: str
    es_base: bool


@dataclass(frozen=True)
class RolMatrizDTO:
    rol: str
    etiqueta: str
    editable: bool
    permisos: list[str]


@dataclass(frozen=True)
class MatrizDTO:
    funciones: list[FuncionDTO]
    roles: list[RolMatrizDTO]
