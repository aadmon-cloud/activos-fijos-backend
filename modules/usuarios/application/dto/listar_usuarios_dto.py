from dataclasses import dataclass


@dataclass
class ListarUsuariosDTO:
    busqueda: str | None = None
    skip: int = 0
    limit: int = 100
