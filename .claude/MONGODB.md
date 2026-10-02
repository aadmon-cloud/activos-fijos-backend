# MongoDB

## Schema de colección

```python
# modules/<modulo>/infrastructure/persistence/mongo/schema/xxx_collection.py
from shared.infrastructure.persistence.mongo.schema.definitions import (
    MongoCollectionDefinition,
    MongoIndexDefinition,
)

XXX_COLLECTION = MongoCollectionDefinition(
    name="xxx",
    validator={
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["campo_obligatorio"],
            "properties": {
                "campo_obligatorio": {"bsonType": "string"},
            },
        }
    },
    indexes=[
        MongoIndexDefinition(
            name="idx_xxx_campo",       # prefijo idx_ para normales, uq_ para únicos
            keys=[("campo", 1)],
        ),
    ],
)
```

Registrar en `shared/infrastructure/persistence/mongo/schema/registry.py` → función `obtener_colecciones_mongo()`.

## Sincronización de schema

```powershell
# Siempre primero dry-run
.\.venv\Scripts\python.exe -m scripts.mongo.sync_schema --dry-run
# Luego aplicar
.\.venv\Scripts\python.exe -m scripts.mongo.sync_schema
# Solo un módulo
.\.venv\Scripts\python.exe -m scripts.mongo.sync_schema --only proyectos
```

## Pipeline builder

```python
# modules/<modulo>/infrastructure/persistence/mongo/pipelines/listar_xxx_pipeline.py
from shared.infrastructure.persistence.mongo.pipeline_builder import ConstructorPipelineBase

class ListarXxxPipelineBuilder(ConstructorPipelineBase["ListarXxxPipelineBuilder"]):
    def filtrar_activos(self) -> "ListarXxxPipelineBuilder":
        return self.agregar({"$match": {"activo": True}})

    def ordenar_por_fecha(self) -> "ListarXxxPipelineBuilder":
        return self.agregar({"$sort": {"fecha": -1, "_id": -1}})
```

Uso en repositorio:
```python
pipeline = (
    ListarXxxPipelineBuilder()
    .filtrar_activos()
    .ordenar_por_fecha()
    .paginar(pagina=pagina, limite=limite)
    .construir()
)
```

Usar builder cuando la consulta tiene 2+ filtros, lookups, proyecciones o paginación. Si es trivial, inline en el repositorio.

## Orden recomendado de pipeline

1. `$match` lo más al inicio posible
2. `$sort` soportado por índice
3. `$lookup` solo si es necesario
4. `$project` para recortar campos
5. Paginación con `facet` o equivalente

## Reglas de índices

- `idx_` prefijo para índices normales
- `uq_` prefijo para índices únicos
- `ttl_` prefijo para índices de expiración (TTL)
- Cada índice responde a una consulta o restricción concreta, no a intuición
- Definir índices desde el diseño inicial, no cuando ya hay lentitud en producción

### Índices TTL (borrado automático)

`MongoIndexDefinition` soporta `expire_after_seconds` para que Mongo borre documentos
viejos según un campo `date`. Gestionar el TTL desde el schema (no a mano en Atlas):

```python
MongoIndexDefinition(
    name="ttl_xxx_fecha",
    keys=[("fecha", 1)],
    expire_after_seconds=2592000,   # 30 días
)
```

- El campo indexado debe ser `bsonType: "date"`.
- `_index_matches` compara `expireAfterSeconds`, así que cambiar el TTL se detecta en el sync.

## Checklist antes de nueva colección

- [ ] Modelada visualmente (Moon Modeler u otra herramienta)
- [ ] Campos obligatorios/opcionales definidos
- [ ] Identificador natural identificado (¿debe ser único?)
- [ ] Índices responden a consultas reales
- [ ] Validator refleja contrato mínimo del documento
- [ ] Archivo en `modules/<modulo>/infrastructure/persistence/mongo/schema/`
- [ ] Registrada en `registry.py`
- [ ] Ejecutado `--dry-run` antes de aplicar
