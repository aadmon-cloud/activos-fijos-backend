# Contexto del proyecto

## Reglas críticas

- Arquitectura hexagonal estricta: `infrastructure → application → domain`
- `domain/` y `application/` no importan FastAPI, Motor ni SDKs cloud
- Acceso a Mongo vía el singleton `mongo_manager` (`shared/infrastructure/persistence/mongo/database.py`), no vía `Depends`
- Antes de crear algo transversal, verificar si pertenece a `shared/`
- Cada módulo expone `register_module()` en su `bootstrap.py`
- Todo cambio de lógica incluye pruebas unitarias
- Sin `__init__.py` en `modules/`/`shared/` (namespace packages)

## Contexto detallado en `.claude/`

| Tarea | Archivo |
|---|---|
| **Flujo de trabajo completo** | `.claude/WORKFLOW.md` |
| Arquitectura y capas | `.claude/ARCHITECTURE.md` |
| Stack y arranque | `.claude/STACK.md` |
| Nombres y patrones | `.claude/CONVENTIONS.md` |
| Endpoints HTTP | `.claude/API.md` |
| MongoDB — convenciones e índices | `.claude/MONGODB.md` |
| MongoDB — modelado de colecciones | `.claude/MONGODB_MODELING.md` |
| MongoDB — construcción de consultas | `.claude/MONGODB_QUERIES.md` |
| Tests | `.claude/TESTING.md` |
| Módulo nuevo | `.claude/TEMPLATE.md` |
| Checklist PR | `.claude/SOLID_CHECKLIST.md` |

Módulo de referencia funcional completo: `modules/tareas/`.
