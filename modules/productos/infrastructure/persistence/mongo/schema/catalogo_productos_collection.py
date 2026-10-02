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

CATALOGO_PRODUCTOS_COLLECTION = MongoCollectionDefinition(
    name="catalogo_productos",
    validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "codigo",
                "nombre",
                "stock_minimo",
                "stock_actual",
                "precio_unitario",
                "creado_por",
            ],
            "properties": {
                "codigo": {"bsonType": "string"},
                "nombre": {"bsonType": "string"},
                "descripcion": {"bsonType": ["string", "null"]},
                "categoria": {"bsonType": ["string", "null"]},
                "stock_minimo": {"bsonType": "int"},
                "stock_actual": {"bsonType": "int"},
                "precio_unitario": {"bsonType": "double"},
                # Incremento futuro del módulo productos (subir/eliminar imagen) —
                # ver MIGRATION_PLAN.md, Fase 1 de `productos`.
                "imagen_url": {"bsonType": ["string", "null"]},
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
            name="uq_catalogo_productos_codigo",
            keys=[("codigo", 1)],
            unique=True,
        ),
        MongoIndexDefinition(
            name="idx_catalogo_productos_nombre_texto",
            keys=[("nombre", "text")],
        ),
        MongoIndexDefinition(
            name="idx_catalogo_productos_categoria",
            keys=[("categoria", 1)],
        ),
        MongoIndexDefinition(
            name="idx_catalogo_productos_stock_actual",
            keys=[("stock_actual", 1)],
        ),
        MongoIndexDefinition(
            name="idx_catalogo_productos_creado_fecha",
            keys=[("creado_por.fecha", -1)],
        ),
    ],
)
