from shared.infrastructure.persistence.mongo.schema.definitions import (
    MongoCollectionDefinition,
    MongoIndexDefinition,
)

CONTADORES_MOVIMIENTOS_COLLECTION = MongoCollectionDefinition(
    name="contadores_movimientos",
    validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["nombre", "prefijo", "ultimo_numero"],
            "properties": {
                "nombre": {"bsonType": "string"},
                "prefijo": {"bsonType": "string"},
                "ultimo_numero": {"bsonType": "int"},
            },
        }
    },
    indexes=[
        MongoIndexDefinition(
            name="uq_contadores_movimientos_nombre",
            keys=[("nombre", 1)],
            unique=True,
        ),
    ],
)
