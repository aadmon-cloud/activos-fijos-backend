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

_PRODUCTO_KIT_REQUIRED = ["producto_id", "cantidad", "producto_nombre"]
_PRODUCTO_KIT_PROPERTIES = {
    "producto_id": {"bsonType": "string"},
    "cantidad": {"bsonType": "int"},
    "producto_nombre": {"bsonType": "string"},
}

CATALOGO_MERCADOS_PREDEFINIDOS_COLLECTION = MongoCollectionDefinition(
    name="catalogo_mercados_predefinidos",
    validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["nombre", "productos", "activo", "creado_por"],
            "properties": {
                "nombre": {"bsonType": "string"},
                "descripcion": {"bsonType": ["string", "null"]},
                "productos": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "required": _PRODUCTO_KIT_REQUIRED,
                        "properties": _PRODUCTO_KIT_PROPERTIES,
                    },
                },
                "activo": {"bsonType": "bool"},
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
            name="uq_catalogo_mercados_predefinidos_nombre",
            keys=[("nombre", 1)],
            unique=True,
        ),
    ],
)
