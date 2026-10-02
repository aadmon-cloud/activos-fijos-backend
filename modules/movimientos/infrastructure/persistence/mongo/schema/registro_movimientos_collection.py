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

_ITEM_MOVIMIENTO_REQUIRED = ["producto_codigo", "producto_nombre", "cantidad"]
_ITEM_MOVIMIENTO_PROPERTIES = {
    "producto_codigo": {"bsonType": "string"},
    "producto_nombre": {"bsonType": "string"},
    "cantidad": {"bsonType": "int"},
    "ubicacion": {"bsonType": ["string", "null"]},
}

REGISTRO_MOVIMIENTOS_COLLECTION = MongoCollectionDefinition(
    name="registro_movimientos",
    validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["tipo", "modalidad", "cantidad", "creado_por"],
            "properties": {
                "tipo": {
                    "enum": [
                        "entrada",
                        "salida",
                        "creacion_ubicacion",
                        "transferencia_ubicacion",
                    ]
                },
                # "creacion_ubicacion"/"transferencia_ubicacion" quedan reservados
                # para el incremento 5 (bitácora de `ubicaciones`) — ver
                # MIGRATION_PLAN.md, Fase 0/1 de `movimientos`.
                "modalidad": {
                    "enum": ["individual", "kit", "multiple", "entrada_multiple", "mercado"]
                },
                # Solo "individual" tiene código en este incremento; el resto
                # queda reservado para los incrementos 2-6.
                "producto_codigo": {"bsonType": ["string", "null"]},
                "producto_nombre": {"bsonType": ["string", "null"]},
                "cantidad": {"bsonType": "int"},
                "motivo": {"bsonType": ["string", "null"]},
                "tipo_origen": {"bsonType": ["string", "null"]},
                "origen_nombre": {"bsonType": ["string", "null"]},
                "cliente_destino": {"bsonType": ["string", "null"]},
                "ubicacion": {"bsonType": ["string", "null"]},
                "ubicacion_origen": {"bsonType": ["string", "null"]},
                "ubicacion_destino": {"bsonType": ["string", "null"]},
                "notas": {"bsonType": ["string", "null"]},
                "remision": {"bsonType": ["string", "null"]},
                "caso": {"bsonType": ["string", "null"]},
                "referencia": {"bsonType": ["string", "null"]},
                "numero_cajas": {"bsonType": ["int", "null"]},
                "kit_nombre": {"bsonType": ["string", "null"]},
                "nombre_mercado": {"bsonType": ["string", "null"]},
                "productos": {
                    "bsonType": ["array", "null"],
                    "items": {
                        "bsonType": "object",
                        "required": _ITEM_MOVIMIENTO_REQUIRED,
                        "properties": _ITEM_MOVIMIENTO_PROPERTIES,
                    },
                },
                "pdf_firmado": {"bsonType": ["string", "null"]},
                "pdf_nombre": {"bsonType": ["string", "null"]},
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
            name="idx_registro_movimientos_producto_codigo",
            keys=[("producto_codigo", 1)],
        ),
        MongoIndexDefinition(
            name="idx_registro_movimientos_productos_codigo",
            keys=[("productos.producto_codigo", 1)],
        ),
        MongoIndexDefinition(
            name="idx_registro_movimientos_fecha",
            keys=[("creado_por.fecha", -1)],
        ),
        MongoIndexDefinition(
            name="idx_registro_movimientos_tipo",
            keys=[("tipo", 1)],
        ),
        MongoIndexDefinition(
            name="idx_registro_movimientos_fecha_tipo",
            keys=[("creado_por.fecha", -1), ("tipo", 1)],
        ),
        MongoIndexDefinition(
            name="idx_registro_movimientos_producto_fecha",
            keys=[("producto_codigo", 1), ("creado_por.fecha", -1)],
        ),
        MongoIndexDefinition(
            name="idx_registro_movimientos_remision",
            keys=[("remision", 1)],
            sparse=True,
        ),
        MongoIndexDefinition(
            name="idx_registro_movimientos_caso",
            keys=[("caso", 1)],
            sparse=True,
        ),
    ],
)
