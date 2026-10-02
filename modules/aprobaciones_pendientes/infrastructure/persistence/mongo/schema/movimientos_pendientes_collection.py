from shared.infrastructure.persistence.mongo.schema.definitions import (
    MongoCollectionDefinition,
    MongoIndexDefinition,
)

_AUDIT_PERSONA_REQUIRED = ["id_persona", "nombre", "fecha"]
_AUDIT_PERSONA_PROPERTIES = {
    "id_persona": {"bsonType": "objectId"},
    "nombre": {"bsonType": "string"},
    "fecha": {"bsonType": "date"},
}

MOVIMIENTOS_PENDIENTES_COLLECTION = MongoCollectionDefinition(
    name="movimientos_pendientes",
    validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["tipo_propuesto", "payload", "estado", "creado_por"],
            "properties": {
                "tipo_propuesto": {
                    "enum": ["entrada", "entrada_multiple", "salida", "salida_multiple"]
                },
                # Forma real validada en la capa de aplicación según
                # `tipo_propuesto` (mismo criterio que `reservas.datos_adicionales`).
                "payload": {"bsonType": "object"},
                "estado": {"enum": ["pendiente", "confirmada"]},
                "movimiento_id": {"bsonType": ["objectId", "null"]},
                "creado_por": {
                    "bsonType": "object",
                    "required": _AUDIT_PERSONA_REQUIRED,
                    "properties": _AUDIT_PERSONA_PROPERTIES,
                },
                "confirmado_por": {
                    "bsonType": ["object", "null"],
                    "required": _AUDIT_PERSONA_REQUIRED,
                    "properties": _AUDIT_PERSONA_PROPERTIES,
                },
            },
        }
    },
    indexes=[
        MongoIndexDefinition(
            name="idx_movimientos_pendientes_estado",
            keys=[("estado", 1)],
        ),
        MongoIndexDefinition(
            name="idx_movimientos_pendientes_creado_por_id_estado",
            keys=[("creado_por.id_persona", 1), ("estado", 1)],
        ),
        MongoIndexDefinition(
            name="idx_movimientos_pendientes_tipo_propuesto",
            keys=[("tipo_propuesto", 1)],
        ),
        MongoIndexDefinition(
            name="idx_movimientos_pendientes_fecha_desc",
            keys=[("creado_por.fecha", -1)],
        ),
    ],
)
