# Convenciones

## Nombres de clases y archivos

| Patrón | Clase | Archivo |
|---|---|---|
| Servicio de aplicación | `CrearTareaService` | `crear_tarea.py` |
| Puerto de repositorio | `TareaRepositoryPort` | `tarea_repository.py` |
| Repositorio Mongo | `MongoTareaRepository` | `mongo_tarea_repository.py` (o `tarea_repository.py`) |
| Pipeline builder | `TareaPipelineBuilder` | `listar_tareas_pipeline.py` |
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
def _doc_a_resumen(doc: dict) -> XxxResumenDTO: ...   # para proyecciones de pipeline
```

Extraer a `xxx_mapper.py` solo cuando el repositorio supera ~200 líneas o hay 3+ tipos de documentos distintos.

## Documentación de código

- Rutas FastAPI: documentar via `summary=`, `responses=`. No usar docstrings en la función.
- Servicios: docstring en `ejecutar()` solo si el contrato no es obvio. Primera línea qué hace; sección `Raises:` listando `DomainError` propios.
- No documentar parámetros obvios por nombre y tipo.

## Errores de dominio

Viven en `domain/errors.py`. Lanzados por servicios de aplicación, capturados por la infraestructura HTTP.

## Sin `__init__.py`

El proyecto usa namespace packages de Python 3.3+. No crear `__init__.py` en ningún directorio de módulo.
