# Nuevo módulo — checklist de construcción

> Este checklist cubre la **Fase 3: Construcción**.  
> Antes de empezar aquí, seguir el flujo completo en `.claude/WORKFLOW.md`.

---

## Fase 0 — Antes de construir (verificar que está hecho)

- [ ] Alcance acordado (Fase 0 de WORKFLOW.md)
- [ ] Schema Mongo aprobado visualmente (Fase 1)
- [ ] Diseño de dominio y servicios aprobado (Fase 2)

---

## 1. Definir el dominio

- [ ] Nombre del módulo en snake_case: `modules/<nombre_modulo>/`
- [ ] Límite de dominio claro (qué responsabilidades incluye y excluye)
- [ ] Identificar entidad principal

## 2. Domain

```
modules/<modulo>/domain/
  entities/<entidad>.py     ← clase Python pura, sin Pydantic ni Motor
  errors.py                 ← excepciones que heredan de DomainError o base propia
```

- [ ] Entidad principal modelada en `domain/entities/`
- [ ] Errores de negocio en `domain/errors.py`
- [ ] Cero imports de FastAPI, Motor, Pydantic en `domain/`

## 3. Application

```
modules/<modulo>/application/
  dto/
    crear_xxx_dto.py
    xxx_dto.py
  ports/
    xxx_repository.py       ← ABC con métodos abstractos
  services/
    crear_xxx.py            ← CrearXxxService con .ejecutar()
```

- [ ] Puerto de repositorio definido como ABC en `application/ports/`
- [ ] DTO de entrada y salida por caso de uso
- [ ] Servicio depende del puerto, no del repositorio concreto
- [ ] Tests unitarios creados para cada servicio

## 4. Infrastructure

```
modules/<modulo>/infrastructure/
  api/
    routes.py               ← router = APIRouter(prefix="/api/xxx", tags=["xxx"])
    schemas.py              ← XxxRequest, XxxResponse (Pydantic)
    dependencies.py         ← get_xxx_service(db) → XxxService(MongoXxxRepository(db))
  persistence/
    mongo/
      schema/
        xxx_collection.py   ← MongoCollectionDefinition + índices
      xxx_repository.py     ← MongoXxxRepository(XxxRepositoryPort)
```

- [ ] Schema de colección en `schema/xxx_collection.py`
- [ ] Colección registrada en `shared/infrastructure/persistence/mongo/schema/registry.py`
- [ ] Repositorio concreto implementa el puerto
- [ ] Mapeo `_doc_a_entidad` / `_entidad_a_doc` inline (o en `xxx_mapper.py` si >200 líneas)
- [ ] Cada endpoint tiene `summary=` y `responses=` con errores 4xx de negocio
- [ ] Dependencies construye el grafo completo de inyección

## 5. Bootstrap

```python
# modules/<modulo>/bootstrap.py
def register_module(app: FastAPI) -> None:
    app.include_router(router)
```

- [ ] `register_module(app)` implementado
- [ ] Registrado en `shared/bootstrap/application.py`

## 6. Schema Mongo

- [ ] Colección modelada visualmente antes de escribir código
- [ ] `--dry-run` ejecutado y revisado
- [ ] Schema sincronizado

## 7. Documentación del módulo

- [ ] Crear `.claude/modules/<MODULO>.md` con: entidades, casos de uso, colecciones, flujos principales
- [ ] Actualizar `.claude/modules/<MODULO>.md` ante cada cambio significativo

## Decisión: ¿módulo o shared?

- Solo aplica a un dominio → `modules/<modulo>/`
- Lo usan varios módulos → evaluar `shared/`
- Integración externa reutilizable → normalmente `shared/infrastructure/`
