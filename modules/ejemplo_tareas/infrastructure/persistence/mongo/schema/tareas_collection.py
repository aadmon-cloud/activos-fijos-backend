from shared.infrastructure.persistence.mongo.schema.definitions import (
    MongoCollectionDefinition,
    MongoIndexDefinition,
)

TAREAS_COLLECTION = MongoCollectionDefinition(
    name="tareas",
    validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["titulo", "completada", "creada_en"],
            "properties": {
                "titulo": {"bsonType": "string"},
                "descripcion": {"bsonType": "string"},
                "completada": {"bsonType": "bool"},
                "creada_en": {"bsonType": "date"},
                "completada_en": {"bsonType": "date"},
            },
        }
    },
    indexes=[
        MongoIndexDefinition(
            name="idx_tareas_creada_en",
            keys=[("creada_en", -1), ("_id", -1)],
        ),
        MongoIndexDefinition(
            name="idx_tareas_completada",
            keys=[("completada", 1)],
        ),
    ],
)
