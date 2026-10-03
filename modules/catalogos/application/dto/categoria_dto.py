from dataclasses import dataclass

from modules.catalogos.domain.entities import Categoria


@dataclass
class CategoriaDTO:
    id: str
    nombre: str
    descripcion: str | None


def categoria_a_dto(categoria: Categoria) -> CategoriaDTO:
    return CategoriaDTO(id=categoria.id, nombre=categoria.nombre, descripcion=categoria.descripcion)
