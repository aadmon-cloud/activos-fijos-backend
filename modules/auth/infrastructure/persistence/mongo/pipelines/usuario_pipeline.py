from __future__ import annotations

from shared.infrastructure.persistence.mongo.pipeline_builder import (
    ConstructorPipelineBase,
)


class UsuarioPipelineBuilder(ConstructorPipelineBase["UsuarioPipelineBuilder"]):
    def ordenar_por_fecha_creacion_desc(self) -> "UsuarioPipelineBuilder":
        return self.agregar({"$sort": {"creado_por.fecha": -1, "_id": -1}})
