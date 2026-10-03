# Convenciones

## Nombres de clases y archivos

| Patrón | Clase | Archivo |
|---|---|---|
| Servicio de aplicación | `CrearTareaService` | `crear_tarea.py` |
| Puerto de repositorio | `TareaRepositoryPort` | `tarea_repository.py` |
| Repositorio Mongo | `MongoTareaRepository` | `tarea_repository.py` |
| DTO de entrada | `CrearTareaDTO` | `crear_tarea_dto.py` |
| DTO de salida | `TareaDTO` | `tarea_dto.py` |
| Schema HTTP | `CrearTareaRequest` / `TareaResponse` | `schemas.py` |
| Mapper (si se extrae) | — | `tarea_mapper.py` |

## Servicios: uno o varios métodos

**Una acción = una clase con `ejecutar()`** cuando cada acción tiene dependencias o permisos distintos:
```python
CrearTareaService.ejecutar()
CambiarEstadoTareaService.ejecutar()
```

**Varios métodos** solo cuando modelan una capacidad compartida cohesionada:
```python
class BuscadorTareasService:
    async def por_proyecto(self, proyecto_id): ...
    async def por_persona(self, persona_id): ...
```

Pregunta guía: ¿si cambias una operación, es probable que debas tocar las otras? Si sí, van juntas.

## Mapeo Mongo ↔ entidad

Funciones privadas (prefijo `_`) en el mismo archivo del repositorio:

```python
def _doc_a_entidad(doc: dict) -> XxxEntity: ...
def _entidad_a_doc(xxx: XxxEntity) -> dict: ...
```

Extraer a `xxx_mapper.py` solo cuando el repositorio supera ~200 líneas o hay 3+ tipos de documentos distintos.

## Documentación de código

- Rutas FastAPI: documentar via `summary=`, `responses=`. No usar docstrings en la función.
- Servicios: docstring en `ejecutar()` solo si el contrato no es obvio.
- No documentar parámetros obvios por nombre y tipo.

## Errores de dominio

Viven en `domain/errors.py`, heredan de `shared.domain.errors.DomainError`.
Cada subclase pasa `code` (prefijo por módulo, ej. `TAR-001`) y `category`
(`shared.domain.errors.ErrorCategory`) a `super().__init__()` — el HTTP status
se deriva de `category`, no se declara aparte. Lanzados por servicios de
aplicación, convertidos a respuestas HTTP por
`shared/infrastructure/api/error_handlers.py`. Ver `.claude/API.md` para el
contrato completo del envelope de error/éxito.

## Sin `__init__.py`

El proyecto usa namespace packages de Python 3.3+. No crear `__init__.py` en ningún directorio de módulo.
