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

STOCK_UBICACIONES_COLLECTION = MongoCollectionDefinition(
    name="stock_ubicaciones",
    validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "producto_codigo",
                "ubicacion",
                "stock_fisico",
                "stock_reservado",
                "creado_por",
            ],
            "properties": {
                "producto_codigo": {"bsonType": "string"},
                "ubicacion": {"bsonType": "string"},
                "stock_fisico": {"bsonType": "int"},
                # Incremento futuro del módulo (reservas) — ver MIGRATION_PLAN.md,
                # Fase 1 de `ubicaciones`.
                "stock_reservado": {"bsonType": "int"},
                "creado_por": {
                    "bsonType": "object",
                    "required": _AUDIT_PERSONA_REQUIRED,
                    "properties": _AUDIT_PERSONA_PROPERTIES,
                },
                "actualizado_por": {
                    "bsonType": ["object", "null"],
                    "required": _AUDIT_PERSONA_REQUIRED,
                    "properties": _AUDIT_PERSONA_PROPERTIES,
                },
            },
        }
    },
    indexes=[
        MongoIndexDefinition(
            name="uq_stock_ubicaciones_producto_ubicacion",
            keys=[("producto_codigo", 1), ("ubicacion", 1)],
            unique=True,
        ),
    ],
)
