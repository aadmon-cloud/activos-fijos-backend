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

_ITEM_RESERVA_REQUIRED = ["producto_codigo", "ubicacion", "cantidad"]
_ITEM_RESERVA_PROPERTIES = {
    "producto_codigo": {"bsonType": "string"},
    "ubicacion": {"bsonType": "string"},
    "cantidad": {"bsonType": "int"},
}

RESERVAS_STOCK_COLLECTION = MongoCollectionDefinition(
    name="reservas_stock",
    validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["session_id", "items", "creado_por", "ultima_actividad"],
            "properties": {
                "session_id": {"bsonType": "string"},
                "items": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": _ITEM_RESERVA_REQUIRED,
                        "properties": _ITEM_RESERVA_PROPERTIES,
                    },
                },
                # Contexto libre para cuando `movimientos` confirme la reserva
                # como salida real — ver MIGRATION_PLAN.md, Fase 1 de `reservas`.
                "datos_adicionales": {"bsonType": ["object", "null"]},
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
                "ultima_actividad": {"bsonType": "date"},
            },
        }
    },
    indexes=[
        MongoIndexDefinition(
            name="uq_reservas_stock_session_id",
            keys=[("session_id", 1)],
            unique=True,
        ),
        MongoIndexDefinition(
            name="idx_reservas_stock_items_producto_codigo",
            keys=[("items.producto_codigo", 1)],
        ),
        MongoIndexDefinition(
            name="ttl_reservas_stock_ultima_actividad",
            keys=[("ultima_actividad", 1)],
            expire_after_seconds=259200,
        ),
    ],
)
