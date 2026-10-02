from __future__ import annotations

from typing import Any

from shared.infrastructure.persistence.mongo.pipeline_builder import (
    ConstructorPipelineBase,
)


class MovimientoPipelineBuilder(ConstructorPipelineBase["MovimientoPipelineBuilder"]):
    def filtrar(self, filtro: dict[str, Any]) -> "MovimientoPipelineBuilder":
        if filtro:
            return self.agregar({"$match": filtro})
        return self

    def ordenar_por_fecha_desc(self) -> "MovimientoPipelineBuilder":
        return self.agregar({"$sort": {"creado_por.fecha": -1, "_id": -1}})
