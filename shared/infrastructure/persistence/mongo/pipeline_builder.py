from __future__ import annotations
from typing import Any, Generic, TypeVar

T = TypeVar("T", bound="ConstructorPipelineBase")

class ConstructorPipelineBase(Generic[T]):
    def __init__(self) -> None:
        self._pipeline: list[dict[str, Any]] = []

    def agregar(self: T, stage: dict[str, Any]) -> T:
        self._pipeline.append(stage)
        return self

    def paginar(self: T, pagina: int, limite: int) -> T:
        """Agrega paginación estándar ($facet). Llamar siempre al final del pipeline."""
        pagina = max(int(pagina or 1), 1)
        limite = max(min(int(limite or 10), 200), 1)
        salto = (pagina - 1) * limite

        tiene_sort = any("$sort" in stage for stage in self._pipeline)
        if not tiene_sort:
            self.agregar({"$sort": {"_id": 1}})

        self.agregar({
            "$facet": {
                "data": [
                    {"$skip": salto},
                    {"$limit": limite}
                ],
                "meta": [
                    {"$count": "total"}
                ]
            }
        })

        self.agregar({
            "$project": {
                "resultado": "$data",
                "total_elementos": {
                    "$ifNull": [{"$arrayElemAt": ["$meta.total", 0]}, 0]
                }
            }
        })

        self.agregar({
            "$addFields": {
                "pagina_actual": pagina,
                "elementos_por_pagina": limite,
                "total_paginas": {
                    "$cond": {
                        "if": {"$gt": ["$total_elementos", 0]},
                        "then": {"$ceil": {"$divide": ["$total_elementos", limite]}},
                        "else": 0
                    }
                }
            }
        })

        return self

    def construir(self) -> list[dict[str, Any]]:
        return self._pipeline
