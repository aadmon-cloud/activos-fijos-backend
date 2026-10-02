from math import ceil
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class RespuestaPaginada(BaseModel, Generic[T]):
    """
    Estructura estandar para respuestas paginadas en el sistema.
    """

    resultado: List[T]
    pagina_actual: int
    elementos_por_pagina: int
    total_elementos: int
    total_paginas: int

    @classmethod
    def crear(cls, items: List[T], page: int, limit: int, total: int):
        limit = limit if limit > 0 else 10
        total_pages = ceil(total / limit)

        return cls(
            resultado=items,
            pagina_actual=page,
            elementos_por_pagina=limit,
            total_elementos=total,
            total_paginas=total_pages,
        )
