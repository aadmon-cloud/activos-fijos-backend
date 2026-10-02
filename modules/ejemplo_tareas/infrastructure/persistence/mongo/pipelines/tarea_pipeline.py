from __future__ import annotations

from shared.infrastructure.persistence.mongo.pipeline_builder import (
    ConstructorPipelineBase,
)


class TareaPipelineBuilder(ConstructorPipelineBase["TareaPipelineBuilder"]):
    """
    Pipeline builder especifico del modulo.

    La clase base vive en `shared` porque es reutilizable.
    Las reglas concretas del agregado viven en el modulo porque
    pertenecen al adaptador de persistencia de esta feature.
    """

    def filtrar_por_estado(
        self,
        completada: bool | None = None,
    ) -> "TareaPipelineBuilder":
        if completada is None:
            return self

        return self.agregar({"$match": {"completada": completada}})

    def buscar_por_texto(self, texto: str | None) -> "TareaPipelineBuilder":
        if not texto:
            return self

        patron = texto.strip()
        if not patron:
            return self

        return self.agregar(
            {
                "$match": {
                    "$or": [
                        {"titulo": {"$regex": patron, "$options": "i"}},
                        {"descripcion": {"$regex": patron, "$options": "i"}},
                    ]
                }
            }
        )

    def ordenar_por_fecha_creacion_desc(self) -> "TareaPipelineBuilder":
        return self.agregar({"$sort": {"creada_en": -1, "_id": -1}})

    def proyectar_resumen(self) -> "TareaPipelineBuilder":
        return self.agregar(
            {
                "$project": {
                    "_id": 1,
                    "titulo": 1,
                    "descripcion": 1,
                    "completada": 1,
                    "creada_en": 1,
                    "completada_en": 1,
                }
            }
        )
