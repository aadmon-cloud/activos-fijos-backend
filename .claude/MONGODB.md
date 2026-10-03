# MongoDB

## Alcance de esta plantilla

Esta plantilla **no** incluye el framework de `MongoCollectionDefinition` /
`registry.py` / script `sync_schema --dry-run` que usa `UltimateBackend`. Los
repositorios de esta plantilla (ver `modules/tareas/infrastructure/persistence/mongo/`)
acceden directo a la colección vía `mongo_manager.get_database()[...]`, sin
una capa de definición/registro de schema.

Si un proyecto concreto necesita ese nivel de gobierno de schema (validators
versionados, sincronización automática, Moon Modeler), se porta desde
`ms-continuum`/`UltimateBackend` como una adición deliberada, no se asume
disponible por defecto.

## Convenciones de índices (sí aplican siempre)

- `idx_` prefijo para índices normales
- `uq_` prefijo para índices únicos
- `ttl_` prefijo para índices de expiración (TTL)
- Cada índice responde a una consulta o restricción concreta, no a intuición
- Definir índices desde el diseño inicial, no cuando ya hay lentitud en producción

## Checklist antes de nueva colección

- [ ] Campos obligatorios/opcionales definidos
- [ ] Identificador natural identificado (¿debe ser único?)
- [ ] Índices responden a consultas reales
- [ ] Mapeo `_doc_a_entidad`/`_entidad_a_doc` implementado en el repositorio
