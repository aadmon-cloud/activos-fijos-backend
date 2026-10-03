# Spec — Contrato de respuesta éxito/error (envelope estilo CEMP)

> **Estado: diseño cerrado y aprobado.**
> Este spec define el contrato de respuesta HTTP que adopta esta plantilla
> (`fastapi-cloud-run`) a partir de ahora, y que se retrofitea también en
> `ms-libreria-stock-snap` (microservicio ya construido a partir de una copia
> anterior de esta plantilla, antes de que este contrato existiera). El
> contrato replica el patrón ya usado en producción por CEMP
> (`UltimateBackend`), para que servicios externos y el equipo frontend vean
> el mismo shape de respuesta sin importar qué backend los sirva.

## 1. Objetivo y alcance

Hasta ahora esta plantilla respondía errores de dominio como
`{"detail": "mensaje"}` (FastAPI genérico) y éxito como el body plano de cada
endpoint, sin envelope. Esto diverge de CEMP, que usa códigos de error por
dominio (`ACC-001`, etc.), categoría, y un envelope `{status, data}` en toda
respuesta exitosa. Se decide adoptar el mismo contrato en la plantilla para
que cualquier microservicio nuevo nazca ya alineado con CEMP, y retrofitear
`ms-libreria-stock-snap` (el primer microservicio construido con la versión
anterior de la plantilla) para que no quede como una excepción.

**Fuera de alcance:**
- El registro de errores internos a Mongo que tiene CEMP para el catch-all de
  excepciones no controladas (`RegistrarErrorInternoService` +
  `logs_errores_internos`) — esa infraestructura no existe en esta plantilla
  y agregarla es un esfuerzo aparte, no pedido aquí. El catch-all de esta
  plantilla solo responde el envelope de error genérico, sin persistir nada.
- Los errores 422 que arma FastAPI automáticamente (validación de
  Pydantic/headers faltantes) — se mantienen con el shape default de
  FastAPI, sin envolver. Mismo precedente que ya usa CEMP (documentado en
  `docs/api/libreria/ACCESOS.md` de `UltimateBackend`: "distinto del 422 que
  arma FastAPI automáticamente").
- Un helper compartido para construir el envelope de éxito — CEMP no usa
  uno (cada ruta arma el `dict` inline), así que replicar exactamente ese
  patrón evita divergir de la fuente que se está imitando.

## 2. Contrato compartido (`shared/`)

### `shared/domain/errors.py`

```python
from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    BUSINESS_RULE = "business_rule"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    INTEGRATION = "integration"
    INTERNAL = "internal"


class DomainError(Exception):
    """Excepcion base para errores de reglas de negocio."""

    def __init__(
        self,
        message: str,
        code: str = "DOMAIN_ERROR",
        category: ErrorCategory = ErrorCategory.BUSINESS_RULE,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.details = details or {}
```

Reemplaza la versión anterior (`DomainError(mensaje); status_code: int = 400`
por subclase). El HTTP status ya **no** lo declara cada subclase — se deriva
de `category` vía el mapeo global (ver abajo), para que código/categoría/HTTP
nunca queden desincronizados entre sí.

### `shared/infrastructure/api/error_handlers.py`

```python
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.domain.errors import DomainError, ErrorCategory

STATUS_BY_CATEGORY = {
    ErrorCategory.VALIDATION: HTTPStatus.BAD_REQUEST,
    ErrorCategory.NOT_FOUND: HTTPStatus.NOT_FOUND,
    ErrorCategory.CONFLICT: HTTPStatus.CONFLICT,
    ErrorCategory.BUSINESS_RULE: HTTPStatus.UNPROCESSABLE_ENTITY,
    ErrorCategory.UNAUTHORIZED: HTTPStatus.UNAUTHORIZED,
    ErrorCategory.FORBIDDEN: HTTPStatus.FORBIDDEN,
    ErrorCategory.INTEGRATION: HTTPStatus.BAD_GATEWAY,
    ErrorCategory.INTERNAL: HTTPStatus.INTERNAL_SERVER_ERROR,
}


def _resolver_status_http(error: DomainError) -> int:
    return int(STATUS_BY_CATEGORY.get(error.category, HTTPStatus.INTERNAL_SERVER_ERROR))


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _manejar_domain_error(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=_resolver_status_http(exc),
            content={
                "status": "error",
                "code": exc.code,
                "message": exc.message,
                "category": exc.category.value,
                "path": request.url.path,
                "metadata": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def _manejar_excepcion_no_controlada(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=int(HTTPStatus.INTERNAL_SERVER_ERROR),
            content={
                "status": "error",
                "code": "GEN-500",
                "message": "Ocurrio un error interno no controlado.",
                "path": request.url.path,
            },
        )
```

Idéntico al mecanismo real de CEMP (`STATUS_BY_CATEGORY`, envelope con
`metadata`), menos el registro a Mongo del catch-all (fuera de alcance, ver
§1) y el handler de `BaseAppException` (no existe `shared_legacy` en esta
plantilla).

### Éxito — sin helper, inline en cada ruta

```python
return {"status": "success", "data": {...}}
return {"status": "success", "message": "...", "data": {"id": "..."}}   # creaciones
return {"status": "success", "message": "..."}                          # acciones sin data
```

Cada handler retorna un `dict` plano (no un `response_model` Pydantic
tipado para el envelope) — mismo patrón que ya usa CEMP.

## 3. Aplicación en el módulo de ejemplo `modules/tareas/`

`domain/errors.py` de `tareas` pasa de:

```python
class TituloTareaVacioError(DomainError):
    status_code = 422
    def __init__(self):
        super().__init__("El titulo de la tarea no puede estar vacio.")
```

a:

```python
class TituloTareaVacioError(DomainError):
    def __init__(self):
        super().__init__(
            "El titulo de la tarea no puede estar vacio.",
            code="TAR-001",
            category=ErrorCategory.BUSINESS_RULE,
        )
```

(`BUSINESS_RULE` preserva el 422 original de este error; `VALIDATION` lo
hubiera cambiado silenciosamente a 400 — bug detectado durante la
implementación.)

Las rutas de `tareas` (`crear_tarea`, `listar_tareas`) pasan a retornar el
envelope de éxito en vez del `TareaResponse` plano.

## 4. Retrofit en `ms-libreria-stock-snap`

Mismo `shared/domain/errors.py` y `shared/infrastructure/api/error_handlers.py`
de §2 (copiados de la plantilla actualizada, no reinventados).

**Códigos de error** (numeración propia — el set de errores de este servicio
es distinto al de CEMP, aunque el prefijo por submódulo se mantiene igual
para que el patrón sea reconocible):

| Código | Categoría | HTTP | Clase | Submódulo |
|---|---|---|---|---|
| `ACC-001` | `not_found` | 404 | `AccesoNoEncontradoError` | `accesos` |
| `ACC-002` | `unauthorized` | 401 | `AccesoNoVigenteError` | `accesos` |
| `CAT-001` | `not_found` | 404 | `ProductoNoEncontradoError` | `catalogo` |
| `CAT-002` | `conflict` | 409 | `ProductoInactivoError` | `catalogo` |
| `INV-001` | `not_found` | 404 | `ProductoSinInventarioEnSitioError` | `inventario` |

**Rutas** — cambian de retornar el `response_model` Pydantic tipado
directamente a retornar el envelope de éxito:

```python
# GET /api/productos/{codigo_barras}
return {
    "status": "success",
    "data": {
        "tipo": producto.tipo,
        "codigo_barras": producto.codigo_barras,
        "nombre": producto.nombre,
        "atributos": producto.atributos,
    },
}

# POST /api/ventas
return {
    "status": "success",
    "data": {
        "precio_venta": venta.precio_venta,
        "moneda": {...},
        "fecha_venta": venta.fecha_venta.isoformat(),
    },
}
```

Los schemas Pydantic (`ProductoResponse`, `VentaResponse`) se mantienen como
la forma del objeto `data` (documentan el shape en Swagger via
`response_model` no aplicado directamente al handler, sino usados para
construir el `dict` de forma consistente) — se elige mantenerlos y
construir el `dict` a partir de `modelo.model_dump()` para no perder la
validación/serialización de Pydantic (fechas, etc.), en vez de armar el
`dict` a mano campo por campo.

**Tests:** cada test de ruta (`test_routes.py` de `inventario` y `ventas`)
se actualiza para verificar `response.json()["data"][...]` en vez de
`response.json()[...]` directo, y los tests de errores verifican
`response.json()["code"]`/`["category"]` en vez de solo el status HTTP.

## 5. Documentación

- `.claude/API.md` y `.claude/CONVENTIONS.md` de la plantilla se actualizan
  para describir el envelope y los códigos de error como el patrón
  estándar (reemplazando las menciones al `{"detail": ...}` anterior).
- `docs/api/LIBRERIA.md` de `ms-libreria-stock-snap` se actualiza: la
  sección "1. Convenciones de respuesta" deja de decir "no usa el envelope
  que sí usa CEMP" — pasa a documentar el mismo envelope, y la sección "5.
  Catálogo de errores" gana la columna `Código` con los 5 códigos de §4.

## 6. Pendiente antes de construir

Ninguno — este spec queda cerrado. Implementación en dos partes: primero la
plantilla (§2-3), después el retrofit de `ms-libreria-stock-snap` (§4-5),
reusando literalmente el código ya definido en §2 en vez de reescribirlo.
