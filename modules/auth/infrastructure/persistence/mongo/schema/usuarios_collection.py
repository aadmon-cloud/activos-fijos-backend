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

USUARIOS_COLLECTION = MongoCollectionDefinition(
    name="usuarios",
    validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "email",
                "username",
                "rol",
                "activo",
                "email_verificado",
                "creado_por",
            ],
            "properties": {
                "email": {"bsonType": "string"},
                "username": {"bsonType": "string"},
                "password_hash": {"bsonType": ["string", "null"]},
                "rol": {
                    "bsonType": "string",
                    "enum": ["super_admin", "admin", "operativo"],
                },
                "activo": {"bsonType": "bool"},
                "email_verificado": {"bsonType": "bool"},
                # Campos de incrementos futuros del módulo auth (Google OAuth,
                # recuperación de password) — ver MIGRATION_PLAN.md, Fase 1 de `auth`.
                "google_id": {"bsonType": ["string", "null"]},
                "google_picture": {"bsonType": ["string", "null"]},
                "reset_password_token": {"bsonType": ["string", "null"]},
                "reset_password_expires": {"bsonType": ["date", "null"]},
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
            name="uq_usuarios_email",
            keys=[("email", 1)],
            unique=True,
        ),
        MongoIndexDefinition(
            name="uq_usuarios_username",
            keys=[("username", 1)],
            unique=True,
        ),
        MongoIndexDefinition(
            name="idx_usuarios_google_id",
            keys=[("google_id", 1)],
            sparse=True,
        ),
        MongoIndexDefinition(
            name="idx_usuarios_reset_token",
            keys=[("reset_password_token", 1)],
            sparse=True,
        ),
        MongoIndexDefinition(
            name="idx_usuarios_creado_fecha",
            keys=[("creado_por.fecha", -1)],
        ),
    ],
)
