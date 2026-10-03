# Envelope de éxito/error estilo CEMP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adoptar en la plantilla `fastapi-cloud-run` y retrofitear en `ms-libreria-stock-snap` el mismo contrato de respuesta que usa CEMP: errores con `code`/`category` derivando el HTTP status, y un envelope `{status, data}`/`{status, message, data}`/`{status, message}` en toda respuesta exitosa.

**Architecture:** Cambio de infraestructura compartida (`shared/domain/errors.py`, `shared/infrastructure/api/error_handlers.py`) más ajustes mecánicos en cada endpoint/error de dominio existente para adoptar el nuevo contrato. Sin cambios de lógica de negocio.

**Tech Stack:** Python 3.12, FastAPI, pytest — igual que ambos repos ya usan.

## Global Constraints

- El HTTP status de un `DomainError` se deriva de `category` vía `STATUS_BY_CATEGORY` (global, en `error_handlers.py`) — ninguna subclase declara `status_code` directamente.
- Categorías y su HTTP: `validation`→400, `not_found`→404, `conflict`→409, `business_rule`→422, `unauthorized`→401, `forbidden`→403, `integration`→502, `internal`→500.
- Los `422` que arma FastAPI automáticamente (validación de Pydantic/headers) **no** se envuelven — quedan con el shape default de FastAPI. No tocar ese comportamiento.
- Sin helper compartido para construir el envelope de éxito — cada ruta retorna el `dict` inline, igual que CEMP.
- Sin registro de errores internos a Mongo en el catch-all genérico — fuera de alcance (ver spec §1).
- No tocar CORS, autenticación, ni ninguna otra configuración de `shared/bootstrap/application.py` más allá de lo que este plan pide.
- Spec de referencia: `docs/superpowers/specs/2026-07-24-error-envelope-design.md`.

---

## Parte A — Plantilla (`fastapi-cloud-run`)

Todos los paths de esta parte son relativos a `C:\Users\FIMLM\Documents\proyectos\fastapi-cloud-run`.

### Task 1: `shared/domain/errors.py` y `shared/infrastructure/api/error_handlers.py`

**Files:**
- Modify: `shared/domain/errors.py`
- Modify: `shared/infrastructure/api/error_handlers.py`
- Modify: `tests/unit/shared/domain/test_errors.py`
- Modify: `tests/unit/shared/infrastructure/api/test_error_handlers.py`

**Interfaces:**
- Produces: `ErrorCategory` (enum), `DomainError(message, code="DOMAIN_ERROR", category=ErrorCategory.BUSINESS_RULE, details=None)`, `STATUS_BY_CATEGORY` — consumidos por Task 2 (mismo repo) y por la Parte B completa (`ms-libreria-stock-snap`).

- [ ] **Step 1: Reemplazar `shared/domain/errors.py`**

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

- [ ] **Step 2: Reemplazar `tests/unit/shared/domain/test_errors.py`**

```python
from shared.domain.errors import DomainError, ErrorCategory


def test_domain_error_expone_message_code_y_category_por_defecto():
    error = DomainError("algo salio mal")

    assert str(error) == "algo salio mal"
    assert error.message == "algo salio mal"
    assert error.code == "DOMAIN_ERROR"
    assert error.category == ErrorCategory.BUSINESS_RULE
    assert error.details == {}


def test_domain_error_permite_code_category_y_details_personalizados():
    error = DomainError(
        "conflicto",
        code="TAR-001",
        category=ErrorCategory.CONFLICT,
        details={"campo": "titulo"},
    )

    assert error.code == "TAR-001"
    assert error.category == ErrorCategory.CONFLICT
    assert error.details == {"campo": "titulo"}
```

- [ ] **Step 3: Correr el test y confirmar que pasa (ya no depende de nada nuevo aparte del archivo reemplazado)**

Run: `python -m pytest tests/unit/shared/domain/test_errors.py -v`
Expected: 2 passed

- [ ] **Step 4: Reemplazar `shared/infrastructure/api/error_handlers.py`**

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

- [ ] **Step 5: Reemplazar `tests/unit/shared/infrastructure/api/test_error_handlers.py`**

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.domain.errors import DomainError, ErrorCategory
from shared.infrastructure.api.error_handlers import register_error_handlers


def _crear_app_de_prueba() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/falla")
    async def falla():
        raise DomainError(
            "recurso duplicado",
            code="TEST-001",
            category=ErrorCategory.CONFLICT,
        )

    @app.get("/falla-no-controlada")
    async def falla_no_controlada():
        raise ValueError("boom")

    return app


def test_domain_error_se_convierte_en_envelope_con_code_category_y_path():
    cliente = TestClient(_crear_app_de_prueba(), raise_server_exceptions=False)

    respuesta = cliente.get("/falla")

    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "status": "error",
        "code": "TEST-001",
        "message": "recurso duplicado",
        "category": "conflict",
        "path": "/falla",
        "metadata": {},
    }


def test_excepcion_no_controlada_se_convierte_en_envelope_gen_500():
    cliente = TestClient(_crear_app_de_prueba(), raise_server_exceptions=False)

    respuesta = cliente.get("/falla-no-controlada")

    assert respuesta.status_code == 500
    assert respuesta.json() == {
        "status": "error",
        "code": "GEN-500",
        "message": "Ocurrio un error interno no controlado.",
        "path": "/falla-no-controlada",
    }
```

`raise_server_exceptions=False` es necesario para el segundo test — de lo contrario `TestClient` re-lanza la excepción no controlada en el proceso de prueba en vez de dejar que el handler la convierta en `500`.

- [ ] **Step 6: Correr ambos archivos de test y confirmar que pasan**

Run: `python -m pytest tests/unit/shared/domain/test_errors.py tests/unit/shared/infrastructure/api/test_error_handlers.py -v`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add shared/domain/errors.py shared/infrastructure/api/error_handlers.py tests/unit/shared/domain/test_errors.py tests/unit/shared/infrastructure/api/test_error_handlers.py
git commit -m "feat: adopta envelope de error con code/category estilo CEMP"
```

---

### Task 2: Actualizar el módulo de ejemplo `modules/tareas/`

**Files:**
- Modify: `modules/tareas/domain/errors.py`
- Modify: `modules/tareas/infrastructure/api/routes.py`
- Modify: `tests/unit/modules/tareas/domain/test_errors.py`
- Modify: `tests/unit/modules/tareas/infrastructure/api/test_routes.py`

**Interfaces:**
- Consumes: `DomainError`, `ErrorCategory` (Task 1).

- [ ] **Step 1: Reemplazar `modules/tareas/domain/errors.py`**

```python
from shared.domain.errors import DomainError, ErrorCategory


class TituloTareaVacioError(DomainError):
    def __init__(self):
        super().__init__(
            "El titulo de la tarea no puede estar vacio.",
            code="TAR-001",
            category=ErrorCategory.BUSINESS_RULE,
        )
```

`category=BUSINESS_RULE` (no `VALIDATION`) para preservar el HTTP `422`
original de este error — `VALIDATION` mapea a `400` en `STATUS_BY_CATEGORY`
(Task 1), y este error es justo el caso que CEMP distingue: una regla de
negocio post-trim (el título quedó vacío tras recortar espacios), no una
validación de shape que Pydantic ya cubre con su propio `422` automático.

- [ ] **Step 2: Reemplazar `tests/unit/modules/tareas/domain/test_errors.py`**

```python
from modules.tareas.domain.errors import TituloTareaVacioError
from shared.domain.errors import ErrorCategory


def test_titulo_tarea_vacio_error_tiene_code_category_y_mensaje():
    error = TituloTareaVacioError()

    assert error.code == "TAR-001"
    assert error.category == ErrorCategory.BUSINESS_RULE
    assert "titulo" in error.message.lower()
```

- [ ] **Step 3: Correr el test y confirmar que pasa**

Run: `python -m pytest tests/unit/modules/tareas/domain/test_errors.py -v`
Expected: 1 passed

- [ ] **Step 4: Reemplazar `modules/tareas/infrastructure/api/routes.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Depends, status

from modules.tareas.application.dto.crear_tarea_dto import CrearTareaDTO
from modules.tareas.application.services.crear_tarea import CrearTareaService
from modules.tareas.application.services.listar_tareas import ListarTareasService
from modules.tareas.infrastructure.api.dependencies import (
    get_crear_tarea_service,
    get_listar_tareas_service,
)
from modules.tareas.infrastructure.api.schemas import CrearTareaRequest, TareaResponse

router = APIRouter(prefix="/api/tareas", tags=["tareas"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Crea una nueva tarea",
    responses={422: {"description": "El titulo de la tarea es invalido"}},
)
async def crear_tarea(
    body: CrearTareaRequest,
    service: Annotated[CrearTareaService, Depends(get_crear_tarea_service)],
):
    tarea = await service.ejecutar(CrearTareaDTO(titulo=body.titulo))
    return {
        "status": "success",
        "message": "Tarea creada exitosamente.",
        "data": TareaResponse(**tarea.__dict__).model_dump(),
    }


@router.get(
    "",
    summary="Lista las tareas existentes",
)
async def listar_tareas(
    service: Annotated[ListarTareasService, Depends(get_listar_tareas_service)],
):
    tareas = await service.ejecutar()
    return {
        "status": "success",
        "data": [TareaResponse(**tarea.__dict__).model_dump() for tarea in tareas],
    }
```

- [ ] **Step 5: Reemplazar `tests/unit/modules/tareas/infrastructure/api/test_routes.py`**

```python
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.tareas.application.services.crear_tarea import CrearTareaService
from modules.tareas.application.services.listar_tareas import ListarTareasService
from modules.tareas.domain.entities import Tarea
from modules.tareas.infrastructure.api.dependencies import (
    get_crear_tarea_service,
    get_listar_tareas_service,
)
from modules.tareas.infrastructure.api.routes import router
from shared.infrastructure.api.error_handlers import register_error_handlers


class _RepositorioEnMemoria(TareaRepositoryPort):
    def __init__(self):
        self._tareas: list[Tarea] = []

    async def guardar(self, tarea: Tarea) -> Tarea:
        tarea_con_id = Tarea(
            id=str(len(self._tareas) + 1),
            titulo=tarea.titulo,
            completada=tarea.completada,
            fecha_creacion=tarea.fecha_creacion,
        )
        self._tareas.append(tarea_con_id)
        return tarea_con_id

    async def listar(self) -> list[Tarea]:
        return list(self._tareas)


def _crear_cliente_de_prueba() -> TestClient:
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(router)

    repositorio = _RepositorioEnMemoria()
    app.dependency_overrides[get_crear_tarea_service] = lambda: CrearTareaService(repositorio)
    app.dependency_overrides[get_listar_tareas_service] = lambda: ListarTareasService(repositorio)

    return TestClient(app)


def test_crear_y_listar_tareas_de_punta_a_punta():
    cliente = _crear_cliente_de_prueba()

    respuesta_crear = cliente.post("/api/tareas", json={"titulo": "Escribir el plan"})
    assert respuesta_crear.status_code == 201
    assert respuesta_crear.json()["status"] == "success"
    assert respuesta_crear.json()["data"]["titulo"] == "Escribir el plan"

    respuesta_listar = cliente.get("/api/tareas")
    assert respuesta_listar.status_code == 200
    assert respuesta_listar.json()["status"] == "success"
    assert len(respuesta_listar.json()["data"]) == 1


def test_crear_tarea_con_titulo_vacio_retorna_422_con_code_tar_001():
    cliente = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/tareas", json={"titulo": "   "})

    assert respuesta.status_code == 422
    assert respuesta.json()["code"] == "TAR-001"
    assert respuesta.json()["category"] == "business_rule"
```

- [ ] **Step 6: Correr todos los tests de `tareas` y confirmar que pasan**

Run: `python -m pytest tests/unit/modules/tareas -v`
Expected: 5 passed (1 domain/test_errors + 2 domain/test_entities + 2 routes; los tests de `application/services` y `infrastructure/persistence` no cambiaron)

Nota: correr `python -m pytest tests/unit/modules/tareas -v` (todo el módulo, no solo `test_errors.py`/`test_routes.py`) para confirmar que ningún otro test del módulo quedó roto por el cambio de shape de respuesta.

- [ ] **Step 7: Commit**

```bash
git add modules/tareas/domain/errors.py modules/tareas/infrastructure/api/routes.py tests/unit/modules/tareas/domain/test_errors.py tests/unit/modules/tareas/infrastructure/api/test_routes.py
git commit -m "feat: adapta el modulo de ejemplo tareas al envelope de error/exito"
```

---

### Task 3: Documentar el contrato en `.claude/API.md` y `.claude/CONVENTIONS.md`

**Files:**
- Modify: `.claude/API.md`
- Modify: `.claude/CONVENTIONS.md`

- [ ] **Step 1: Reemplazar todo el contenido de `.claude/API.md`**

```markdown
# API — Patrones HTTP

## Ruta estándar

```python
# modules/<modulo>/infrastructure/api/routes.py
router = APIRouter(prefix="/api/xxx", tags=["xxx"])

@router.post(
    "",
    status_code=201,
    summary="Crea un nuevo xxx",
    responses={
        409: {"description": "Conflicto de negocio (p. ej. duplicado)"},
        422: {"description": "Datos de entrada inválidos"},
    },
)
async def crear_xxx(
    body: CrearXxxRequest,
    service: Annotated[CrearXxxService, Depends(get_crear_xxx_service)],
):
    resultado = await service.ejecutar(CrearXxxDTO(...))
    return {
        "status": "success",
        "message": "Xxx creado exitosamente.",
        "data": XxxResponse(...).model_dump(),
    }
```

## Envelope de respuesta

Toda ruta retorna un `dict` plano (no un `response_model` Pydantic aplicado al
envelope en sí) con una de estas tres formas de éxito:

```python
{"status": "success", "data": {...}}                            # consultas
{"status": "success", "message": "...", "data": {"id": "..."}}  # creaciones
{"status": "success", "message": "..."}                         # acciones sin data
```

`XxxResponse` (el schema Pydantic) sigue existiendo y documentando el shape en
Swagger — se usa para construir el contenido de `data` vía `.model_dump()`, no
como `response_model` directo del endpoint.

## Inyección de dependencias

```python
# modules/<modulo>/infrastructure/api/dependencies.py
from functools import lru_cache


@lru_cache(maxsize=1)
def get_xxx_repository() -> XxxRepositoryPort:
    return MongoXxxRepository()


def get_crear_xxx_service() -> CrearXxxService:
    return CrearXxxService(xxx_repository=get_xxx_repository())
```

La ruta recibe el servicio ya construido. Nunca instanciar repositorios o servicios dentro del handler.

## Reglas de documentación

- `summary` obligatorio: verbo en tercera persona ("Crea", "Obtiene", "Lista", "Elimina").
- `responses` solo para errores 4xx de negocio relevantes. No documentar 500.
- No usar `description=` en el decorador salvo comportamiento no obvio.
- No docstrings en la función de ruta.

## Schemas HTTP

Viven en `infrastructure/api/schemas.py`. Separar request de response:

```python
class CrearXxxRequest(BaseModel): ...
class XxxResponse(BaseModel): ...
```

## Registro del módulo

```python
# modules/<modulo>/bootstrap.py
def register_module(app: FastAPI) -> None:
    app.include_router(router)
```

Registrado en `shared/bootstrap/application.py`.

## Manejo de errores de dominio

Los errores de dominio (`DomainError` y subclases) se capturan globalmente en
`shared/infrastructure/api/error_handlers.py` y se convierten a:

```json
{
  "status": "error",
  "code": "XXX-001",
  "message": "mensaje legible",
  "category": "not_found",
  "path": "/api/xxx/123",
  "metadata": {}
}
```

El HTTP status se deriva de `category` vía `STATUS_BY_CATEGORY` (no se declara
por subclase):

| Categoría | HTTP |
|---|---|
| `validation` | 400 |
| `not_found` | 404 |
| `conflict` | 409 |
| `business_rule` | 422 |
| `unauthorized` | 401 |
| `forbidden` | 403 |
| `integration` | 502 |
| `internal` | 500 |

Cada subclase de `DomainError` pasa `code` y `category` a `super().__init__()`:

```python
class XxxNoEncontradoError(DomainError):
    def __init__(self, id_xxx: str):
        super().__init__(
            f"El xxx '{id_xxx}' no existe.",
            code="XXX-001",
            category=ErrorCategory.NOT_FOUND,
        )
```

Cualquier excepción no controlada (no `DomainError`) se convierte en un `500`
con `code: "GEN-500"`, sin registro adicional — no debe llegar al cliente
como un error sin envelope.

Los errores `422` que arma FastAPI automáticamente (body/query no cumple el
schema Pydantic) **no** pasan por este envelope — quedan con el shape default
de FastAPI (`{"detail": [...]}`), distinto de un `DomainError` de categoría
`validation`.
```

- [ ] **Step 2: Reemplazar la sección "Errores de dominio" de `.claude/CONVENTIONS.md`**

Buscar el bloque actual:

```markdown
## Errores de dominio

Viven en `domain/errors.py`, heredan de `shared.domain.errors.DomainError`. Lanzados por servicios de aplicación, convertidos a respuestas HTTP por `shared/infrastructure/api/error_handlers.py`.
```

Reemplazarlo por:

```markdown
## Errores de dominio

Viven en `domain/errors.py`, heredan de `shared.domain.errors.DomainError`.
Cada subclase pasa `code` (prefijo por módulo, ej. `TAR-001`) y `category`
(`shared.domain.errors.ErrorCategory`) a `super().__init__()` — el HTTP status
se deriva de `category`, no se declara aparte. Lanzados por servicios de
aplicación, convertidos a respuestas HTTP por
`shared/infrastructure/api/error_handlers.py`. Ver `.claude/API.md` para el
contrato completo del envelope de error/éxito.
```

(el resto de `.claude/CONVENTIONS.md` no cambia)

- [ ] **Step 3: Commit**

```bash
git add .claude/API.md .claude/CONVENTIONS.md
git commit -m "docs: documenta el envelope de error/exito y los codigos de dominio"
```

---

## Parte B — Retrofit (`ms-libreria-stock-snap`)

Todos los paths de esta parte son relativos a `C:\Users\FIMLM\Documents\proyectos\ms-libreria-stock-snap`. El código de `shared/` es idéntico al que produjo la Task 1 (mismo contrato, repo distinto) — no requiere que la Parte A ya esté commiteada allí, se transcribe igual.

### Task 4: `shared/domain/errors.py` y `shared/infrastructure/api/error_handlers.py`

**Files:**
- Modify: `shared/domain/errors.py`
- Modify: `shared/infrastructure/api/error_handlers.py`
- Modify: `tests/unit/shared/domain/test_errors.py`
- Modify: `tests/unit/shared/infrastructure/api/test_error_handlers.py`

**Interfaces:**
- Produces: `ErrorCategory`, `DomainError(message, code, category, details)`, `STATUS_BY_CATEGORY` — idéntico a la Parte A, Task 1. Consumido por Tasks 5 y 6 de esta Parte B.

- [ ] **Step 1: Reemplazar `shared/domain/errors.py`** — mismo contenido exacto que Parte A, Task 1, Step 1.

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

- [ ] **Step 2: Reemplazar `tests/unit/shared/domain/test_errors.py`**

```python
from shared.domain.errors import DomainError, ErrorCategory


def test_domain_error_expone_message_code_y_category_por_defecto():
    error = DomainError("algo salio mal")

    assert str(error) == "algo salio mal"
    assert error.message == "algo salio mal"
    assert error.code == "DOMAIN_ERROR"
    assert error.category == ErrorCategory.BUSINESS_RULE
    assert error.details == {}


def test_domain_error_permite_code_category_y_details_personalizados():
    error = DomainError(
        "conflicto",
        code="TAR-001",
        category=ErrorCategory.CONFLICT,
        details={"campo": "titulo"},
    )

    assert error.code == "TAR-001"
    assert error.category == ErrorCategory.CONFLICT
    assert error.details == {"campo": "titulo"}
```

- [ ] **Step 3: Correr el test y confirmar que pasa**

Run: `python -m pytest tests/unit/shared/domain/test_errors.py -v`
Expected: 2 passed

- [ ] **Step 4: Reemplazar `shared/infrastructure/api/error_handlers.py`**

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

- [ ] **Step 5: Reemplazar `tests/unit/shared/infrastructure/api/test_error_handlers.py`**

```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.domain.errors import DomainError, ErrorCategory
from shared.infrastructure.api.error_handlers import register_error_handlers


def _crear_app_de_prueba() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/falla")
    async def falla():
        raise DomainError(
            "recurso duplicado",
            code="TEST-001",
            category=ErrorCategory.CONFLICT,
        )

    @app.get("/falla-no-controlada")
    async def falla_no_controlada():
        raise ValueError("boom")

    return app


def test_domain_error_se_convierte_en_envelope_con_code_category_y_path():
    cliente = TestClient(_crear_app_de_prueba(), raise_server_exceptions=False)

    respuesta = cliente.get("/falla")

    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "status": "error",
        "code": "TEST-001",
        "message": "recurso duplicado",
        "category": "conflict",
        "path": "/falla",
        "metadata": {},
    }


def test_excepcion_no_controlada_se_convierte_en_envelope_gen_500():
    cliente = TestClient(_crear_app_de_prueba(), raise_server_exceptions=False)

    respuesta = cliente.get("/falla-no-controlada")

    assert respuesta.status_code == 500
    assert respuesta.json() == {
        "status": "error",
        "code": "GEN-500",
        "message": "Ocurrio un error interno no controlado.",
        "path": "/falla-no-controlada",
    }
```

- [ ] **Step 6: Correr ambos archivos de test y confirmar que pasan**

Run: `python -m pytest tests/unit/shared/domain/test_errors.py tests/unit/shared/infrastructure/api/test_error_handlers.py -v`
Expected: 4 passed

- [ ] **Step 7: Commit**

```bash
git add shared/domain/errors.py shared/infrastructure/api/error_handlers.py tests/unit/shared/domain/test_errors.py tests/unit/shared/infrastructure/api/test_error_handlers.py
git commit -m "$(cat <<'EOF'
main
♻️ refactor: adopta envelope de error con code/category estilo CEMP
EOF
)"
```

---

### Task 5: Códigos de error en los 5 `DomainError` de `libreria`

**Files:**
- Modify: `modules/libreria/submodules/accesos/domain/errors.py`
- Modify: `modules/libreria/submodules/catalogo/domain/errors.py`
- Modify: `modules/libreria/submodules/inventario/domain/errors.py`
- Modify: `tests/unit/modules/libreria/submodules/accesos/domain/test_errors.py`
- Modify: `tests/unit/modules/libreria/submodules/catalogo/domain/test_errors.py`
- Modify: `tests/unit/modules/libreria/submodules/inventario/domain/test_errors.py`

**Interfaces:**
- Consumes: `DomainError`, `ErrorCategory` (Task 4).
- Produces: cada error ahora expone `.code`/`.category` en vez de `.status_code` — consumido por Task 6 (las rutas no cambian su manejo de excepciones, pero los tests de ruta de Task 6 verifican estos códigos en las respuestas).

- [ ] **Step 1: Reemplazar `modules/libreria/submodules/accesos/domain/errors.py`**

```python
from shared.domain.errors import DomainError, ErrorCategory


class AccesoNoEncontradoError(DomainError):
    def __init__(self, id_acceso: str):
        super().__init__(
            f"El acceso '{id_acceso}' no existe.",
            code="ACC-001",
            category=ErrorCategory.NOT_FOUND,
        )


class AccesoNoVigenteError(DomainError):
    def __init__(self, id_acceso: str):
        super().__init__(
            f"El acceso '{id_acceso}' esta revocado o vencido.",
            code="ACC-002",
            category=ErrorCategory.UNAUTHORIZED,
        )
```

- [ ] **Step 2: Reemplazar `tests/unit/modules/libreria/submodules/accesos/domain/test_errors.py`**

```python
from modules.libreria.submodules.accesos.domain.errors import AccesoNoEncontradoError, AccesoNoVigenteError
from shared.domain.errors import ErrorCategory


def test_acceso_no_encontrado_error_tiene_code_acc_001_y_categoria_not_found():
    error = AccesoNoEncontradoError("abc123")
    assert error.code == "ACC-001"
    assert error.category == ErrorCategory.NOT_FOUND
    assert "abc123" in error.message


def test_acceso_no_vigente_error_tiene_code_acc_002_y_categoria_unauthorized():
    error = AccesoNoVigenteError("abc123")
    assert error.code == "ACC-002"
    assert error.category == ErrorCategory.UNAUTHORIZED
    assert "abc123" in error.message
```

- [ ] **Step 3: Reemplazar `modules/libreria/submodules/catalogo/domain/errors.py`**

```python
from shared.domain.errors import DomainError, ErrorCategory


class ProductoNoEncontradoError(DomainError):
    def __init__(self, codigo_barras: str):
        super().__init__(
            f"El producto con codigo de barras '{codigo_barras}' no existe.",
            code="CAT-001",
            category=ErrorCategory.NOT_FOUND,
        )


class ProductoInactivoError(DomainError):
    def __init__(self, codigo_barras: str):
        super().__init__(
            f"El producto con codigo de barras '{codigo_barras}' esta inactivo.",
            code="CAT-002",
            category=ErrorCategory.CONFLICT,
        )
```

- [ ] **Step 4: Reemplazar `tests/unit/modules/libreria/submodules/catalogo/domain/test_errors.py`**

```python
from modules.libreria.submodules.catalogo.domain.errors import ProductoInactivoError, ProductoNoEncontradoError
from shared.domain.errors import ErrorCategory


def test_producto_no_encontrado_error_tiene_code_cat_001_y_categoria_not_found():
    error = ProductoNoEncontradoError("7501234567890")
    assert error.code == "CAT-001"
    assert error.category == ErrorCategory.NOT_FOUND
    assert "7501234567890" in error.message


def test_producto_inactivo_error_tiene_code_cat_002_y_categoria_conflict():
    error = ProductoInactivoError("7501234567890")
    assert error.code == "CAT-002"
    assert error.category == ErrorCategory.CONFLICT
    assert "7501234567890" in error.message
```

- [ ] **Step 5: Reemplazar `modules/libreria/submodules/inventario/domain/errors.py`**

```python
from shared.domain.errors import DomainError, ErrorCategory


class ProductoSinInventarioEnSitioError(DomainError):
    def __init__(self, codigo_barras: str):
        super().__init__(
            f"El producto '{codigo_barras}' no tiene inventario asignado a este sitio.",
            code="INV-001",
            category=ErrorCategory.NOT_FOUND,
        )
```

- [ ] **Step 6: Reemplazar `tests/unit/modules/libreria/submodules/inventario/domain/test_errors.py`**

```python
from modules.libreria.submodules.inventario.domain.errors import ProductoSinInventarioEnSitioError
from shared.domain.errors import ErrorCategory


def test_producto_sin_inventario_en_sitio_error_tiene_code_inv_001_y_categoria_not_found():
    error = ProductoSinInventarioEnSitioError("7501234567890")
    assert error.code == "INV-001"
    assert error.category == ErrorCategory.NOT_FOUND
    assert "7501234567890" in error.message
```

- [ ] **Step 7: Correr los 3 archivos de test y confirmar que pasan**

Run: `python -m pytest tests/unit/modules/libreria/submodules/accesos/domain/test_errors.py tests/unit/modules/libreria/submodules/catalogo/domain/test_errors.py tests/unit/modules/libreria/submodules/inventario/domain/test_errors.py -v`
Expected: 5 passed

**Nota — esto rompe temporalmente los tests de ruta existentes** (`test_routes.py` de `inventario` y `ventas` esperan `respuesta.status_code == 404` contra un `DomainError` que ya no declara `status_code` — como el status ahora se deriva de `category`, y las categorías elegidas mapean exactamente a los mismos HTTP que antes (`not_found`→404, `conflict`→409, `unauthorized`→401), el status code observado en runtime no cambia; lo que sí rompe son las aserciones que la Task 6 actualiza sobre el *body* de la respuesta (`cuerpo["data"][...]` en vez de `cuerpo[...]` directo). No correr la suite completa todavía — se corre al final de la Task 6.

- [ ] **Step 8: Commit**

```bash
git add modules/libreria/submodules/accesos/domain/errors.py modules/libreria/submodules/catalogo/domain/errors.py modules/libreria/submodules/inventario/domain/errors.py tests/unit/modules/libreria/submodules/accesos/domain/test_errors.py tests/unit/modules/libreria/submodules/catalogo/domain/test_errors.py tests/unit/modules/libreria/submodules/inventario/domain/test_errors.py
git commit -m "$(cat <<'EOF'
main
♻️ refactor(libreria): agrega code/category a los errores de dominio
EOF
)"
```

---

### Task 6: Envelope de éxito en las 2 rutas HTTP

**Files:**
- Modify: `modules/libreria/submodules/inventario/infrastructure/api/routes.py`
- Modify: `modules/libreria/submodules/ventas/infrastructure/api/routes.py`
- Modify: `tests/unit/modules/libreria/submodules/inventario/infrastructure/api/test_routes.py`
- Modify: `tests/unit/modules/libreria/submodules/ventas/infrastructure/api/test_routes.py`

**Interfaces:**
- Consumes: `ProductoResponse`, `VentaResponse` (schemas ya existentes, sin cambios), códigos de error de Task 5.

- [ ] **Step 1: Reemplazar `modules/libreria/submodules/inventario/infrastructure/api/routes.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from modules.libreria.submodules.accesos.domain.entities import AccesoVenta
from modules.libreria.submodules.accesos.infrastructure.api.dependencies import obtener_acceso_vigente
from modules.libreria.submodules.inventario.application.services.consultar_producto_disponible import (
    ConsultarProductoDisponibleService,
)
from modules.libreria.submodules.inventario.infrastructure.api.dependencies import (
    get_consultar_producto_disponible_service,
)
from modules.libreria.submodules.inventario.infrastructure.api.schemas import ProductoResponse

router = APIRouter(prefix="/api/productos", tags=["catalogo"])


@router.get(
    "/{codigo_barras}",
    summary="Consulta un producto por codigo de barras",
    responses={
        404: {"description": "Producto no encontrado o sin inventario en el sitio"},
        409: {"description": "Producto inactivo"},
    },
)
async def consultar_producto(
    codigo_barras: str,
    acceso: Annotated[AccesoVenta, Depends(obtener_acceso_vigente)],
    service: Annotated[ConsultarProductoDisponibleService, Depends(get_consultar_producto_disponible_service)],
):
    producto = await service.ejecutar(codigo_barras, acceso.id_sitio)
    return {
        "status": "success",
        "data": ProductoResponse(
            tipo=producto.tipo,
            codigo_barras=producto.codigo_barras,
            nombre=producto.nombre,
            atributos=producto.atributos,
        ).model_dump(),
    }
```

- [ ] **Step 2: Reemplazar `modules/libreria/submodules/ventas/infrastructure/api/routes.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Depends, status

from modules.libreria.submodules.accesos.domain.entities import AccesoVenta
from modules.libreria.submodules.accesos.infrastructure.api.dependencies import obtener_acceso_vigente
from modules.libreria.submodules.ventas.application.dto.registrar_venta_dto import RegistrarVentaDTO
from modules.libreria.submodules.ventas.application.services.registrar_venta import RegistrarVentaService
from modules.libreria.submodules.ventas.infrastructure.api.dependencies import get_registrar_venta_service
from modules.libreria.submodules.ventas.infrastructure.api.schemas import RegistrarVentaRequest, VentaResponse

router = APIRouter(prefix="/api/ventas", tags=["ventas"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Registra la venta de un producto y descuenta el inventario",
    responses={
        404: {"description": "Producto no encontrado o sin inventario en el sitio"},
        409: {"description": "Producto inactivo"},
    },
)
async def registrar_venta(
    body: RegistrarVentaRequest,
    acceso: Annotated[AccesoVenta, Depends(obtener_acceso_vigente)],
    service: Annotated[RegistrarVentaService, Depends(get_registrar_venta_service)],
):
    venta = await service.ejecutar(
        RegistrarVentaDTO(codigo_barras=body.codigo_barras, id_transaccion_externa=body.id_transaccion_externa),
        acceso,
    )
    return {
        "status": "success",
        "message": "Venta registrada exitosamente.",
        "data": VentaResponse(
            precio_venta=venta.precio_venta,
            moneda=venta.moneda,
            fecha_venta=venta.fecha_venta,
        ).model_dump(),
    }
```

- [ ] **Step 3: Reemplazar las 2 funciones de test en `tests/unit/modules/libreria/submodules/inventario/infrastructure/api/test_routes.py`**

Mantener las clases `_ProductoRepositorioFalso`, `_LoteRepositorioFalso`, `_acceso_vigente`, `_crear_cliente_de_prueba` tal cual están (no cambian). Reemplazar solo las 2 funciones de test al final del archivo:

```python
def test_consultar_producto_no_incluye_estado_en_la_respuesta():
    cliente = _crear_cliente_de_prueba()

    respuesta = cliente.get("/api/productos/7501234567890", headers={"X-Acceso-Id": "a1"})

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "success"
    assert "estado" not in cuerpo["data"]
    assert cuerpo["data"]["codigo_barras"] == "7501234567890"


def test_consultar_producto_inexistente_retorna_404_con_code_cat_001():
    cliente = _crear_cliente_de_prueba()

    respuesta = cliente.get("/api/productos/no-existe", headers={"X-Acceso-Id": "a1"})

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "CAT-001"
    assert respuesta.json()["category"] == "not_found"
```

- [ ] **Step 4: Reemplazar la función de test en `tests/unit/modules/libreria/submodules/ventas/infrastructure/api/test_routes.py`**

Mantener `_RegistrarVentaServiceFalso`, `_acceso_vigente`, `_crear_cliente_de_prueba` tal cual están. Reemplazar solo la función de test:

```python
def test_registrar_venta_no_expone_datos_internos_en_la_respuesta():
    cliente = _crear_cliente_de_prueba()

    respuesta = cliente.post(
        "/api/ventas",
        json={"codigo_barras": "7501234567890", "id_transaccion_externa": "tx-1"},
        headers={"X-Acceso-Id": "a1"},
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "success"
    datos = cuerpo["data"]
    assert datos["precio_venta"] == 27000.0
    assert "id_lote" not in datos
    assert "vendido_por" not in datos
    assert "id_acceso" not in datos
```

- [ ] **Step 5: Correr los tests de ambas rutas y confirmar que pasan**

Run: `python -m pytest tests/unit/modules/libreria/submodules/inventario/infrastructure/api tests/unit/modules/libreria/submodules/ventas/infrastructure/api -v`
Expected: 3 passed (2 de inventario, 1 de ventas)

- [ ] **Step 6: Correr la suite completa del repo y confirmar que todo pasa**

Run: `python -m pytest -q`
Expected: todos los tests pasan (49 antes de esta parte + los ajustes de Tasks 4-6, sin ningún test roto)

- [ ] **Step 7: Commit**

```bash
git add modules/libreria/submodules/inventario/infrastructure/api/routes.py modules/libreria/submodules/ventas/infrastructure/api/routes.py tests/unit/modules/libreria/submodules/inventario/infrastructure/api/test_routes.py tests/unit/modules/libreria/submodules/ventas/infrastructure/api/test_routes.py
git commit -m "$(cat <<'EOF'
main
♻️ refactor(libreria): envuelve las respuestas exitosas de GET productos y POST ventas
EOF
)"
```

---

### Task 7: Actualizar `docs/api/LIBRERIA.md`

**Files:**
- Modify: `docs/api/LIBRERIA.md`

- [ ] **Step 1: Reemplazar la sección "1. Convenciones de respuesta"**

Buscar el bloque que empieza en `## 1. Convenciones de respuesta` y termina justo antes de `## 2. Tipos y enums`. Reemplazarlo completo por:

```markdown
## 1. Convenciones de respuesta

**Éxito:**

```json
{ "status": "success", "data": { ... } }
{ "status": "success", "message": "…", "data": { ... } }   // ej. registrar venta
```

**Error:**

```json
{
  "status": "error",
  "code": "ACC-002",
  "message": "El acceso '665f4d5e6f7a8b9c0d1e2f30' esta revocado o vencido.",
  "category": "unauthorized",
  "path": "/api/productos/7501234567890",
  "metadata": {}
}
```

Cuando el error es un `422` armado automáticamente por FastAPI (falta el
header `X-Acceso-Id`, o el body no cumple el schema), la respuesta **no** usa
este envelope — queda con el shape default de FastAPI:

```json
{ "detail": [{ "type": "missing", "loc": ["header", "x-acceso-id"], "msg": "Field required" }] }
```

| Categoría | HTTP |
|---|---|
| `not_found` | 404 |
| `conflict` | 409 |
| `unauthorized` | 401 |
```

- [ ] **Step 2: Actualizar la sección "5. Catálogo de errores"**

Buscar el bloque:

```markdown
## 5. Catálogo de errores

Este servicio no usa códigos de dominio (`XXX-nnn`) — solo HTTP + mensaje:

| HTTP | Cuándo ocurre | Acción sugerida en UI |
|---|---|---|
| 401 | Acceso revocado o vencido | Mostrar que el acceso ya no es válido; el vendedor debe pedirle uno nuevo al pastor |
| 404 | Acceso, o producto, no existen; o el producto no tiene inventario en el sitio | Si es al escanear: mostrar "producto no disponible" sin distinguir la causa exacta al usuario final |
| 409 | Producto inactivo | Mostrar "producto no disponible actualmente" |
| 422 | Falta el header `X-Acceso-Id`, o el body está mal formado | Error de integración del frontend, no debería llegar a mostrarse al vendedor en un flujo correcto |
```

Reemplazarlo por:

```markdown
## 5. Catálogo de errores

| Código | HTTP | Categoría | Significado | Acción sugerida en UI |
|---|---|---|---|---|
| `ACC-001` | 404 | `not_found` | El acceso del header no existe | Tratar igual que `ACC-002` — el vendedor no puede seguir |
| `ACC-002` | 401 | `unauthorized` | El acceso está revocado o vencido | Mostrar que el acceso ya no es válido; el vendedor debe pedirle uno nuevo al pastor |
| `CAT-001` | 404 | `not_found` | El producto no existe | Mostrar "producto no disponible" |
| `CAT-002` | 409 | `conflict` | El producto existe pero está inactivo | Mostrar "producto no disponible actualmente" |
| `INV-001` | 404 | `not_found` | El producto no tiene inventario (no anulado) asignado al sitio del acceso | Mostrar "producto no disponible" |

Los `422` que arma FastAPI automáticamente (falta el header `X-Acceso-Id`, o
el body está mal formado) no llevan `código`/`categoría` — son un error de
integración del frontend, no debería llegar a mostrarse al vendedor en un
flujo correcto.
```

- [ ] **Step 3: Revisar y actualizar las menciones de "Errores posibles" en la sección "4. Endpoints"**

En el bloque de `GET /api/productos/{codigo_barras}`, el texto:

```markdown
**Errores posibles:**
- `401` — el acceso del header está revocado o vencido.
- `404` — el acceso no existe; o el producto no existe; o el producto existe
  pero no tiene ningún lote de inventario (no anulado) asignado al sitio del
  acceso.
- `409` — el producto existe pero está inactivo.
- `422` — falta el header `X-Acceso-Id`.
```

pasa a:

```markdown
**Errores posibles:**
- `ACC-002` (401) — el acceso del header está revocado o vencido.
- `ACC-001` (404) — el acceso no existe.
- `CAT-001` (404) — el producto no existe.
- `INV-001` (404) — el producto existe pero no tiene ningún lote de
  inventario (no anulado) asignado al sitio del acceso.
- `CAT-002` (409) — el producto existe pero está inactivo.
- `422` (sin código) — falta el header `X-Acceso-Id`.
```

Y en el bloque de `POST /api/ventas`, el texto:

```markdown
**Errores posibles:**
- `401` — el acceso del header está revocado o vencido.
- `404` — el acceso no existe; o el producto no existe; o el producto no tiene
  inventario (no anulado) asignado al sitio del acceso.
- `409` — el producto está inactivo.
- `422` — falta el header `X-Acceso-Id`, o el body no trae `codigo_barras`/
  `id_transaccion_externa`.
```

pasa a:

```markdown
**Errores posibles:**
- `ACC-002` (401) — el acceso del header está revocado o vencido.
- `ACC-001` (404) — el acceso no existe.
- `CAT-001` (404) — el producto no existe.
- `INV-001` (404) — el producto no tiene inventario (no anulado) asignado al
  sitio del acceso.
- `CAT-002` (409) — el producto está inactivo.
- `422` (sin código) — falta el header `X-Acceso-Id`, o el body no trae
  `codigo_barras`/`id_transaccion_externa`.
```

- [ ] **Step 4: Actualizar los ejemplos de respuesta de éxito en la sección "4. Endpoints"**

El ejemplo de respuesta 200 de `GET /api/productos/{codigo_barras}` pasa de:

```json
{
  "tipo": "biblia",
  "codigo_barras": "7501234567890",
  "nombre": "Biblia Reina Valera 1960 - Letra Grande",
  "atributos": { ... }
}
```

a:

```json
{
  "status": "success",
  "data": {
    "tipo": "biblia",
    "codigo_barras": "7501234567890",
    "nombre": "Biblia Reina Valera 1960 - Letra Grande",
    "atributos": {
      "color": "negro",
      "tamano_fisico": "grande",
      "tamano_letra": "grande",
      "tipo_tapa": "cuero"
    }
  }
}
```

El ejemplo de respuesta 201 de `POST /api/ventas` pasa de:

```json
{
  "precio_venta": 27000.0,
  "moneda": { "divisa": "COP", "nombre_divisa": "Peso Colombiano", "simbolo_divisa": "$" },
  "fecha_venta": "2026-07-23T15:42:10Z"
}
```

a:

```json
{
  "status": "success",
  "message": "Venta registrada exitosamente.",
  "data": {
    "precio_venta": 27000.0,
    "moneda": { "divisa": "COP", "nombre_divisa": "Peso Colombiano", "simbolo_divisa": "$" },
    "fecha_venta": "2026-07-23T15:42:10Z"
  }
}
```

- [ ] **Step 5: Commit**

```bash
git add docs/api/LIBRERIA.md
git commit -m "$(cat <<'EOF'
main
📝 docs(api): actualiza la guia de frontend al envelope de error/exito con codigos
EOF
)"
```

---

## Self-Review

**Spec coverage:**
- §2 (contrato compartido `shared/`) → Tasks 1 y 4 (uno por repo, código idéntico).
- §3 (módulo de ejemplo `tareas`) → Task 2.
- §4 (retrofit `ms-libreria-stock-snap`: códigos + rutas) → Tasks 5 y 6.
- §5 (documentación) → Tasks 3 y 7 (uno por repo).
- §1 (fuera de alcance: logging a Mongo, helper de envelope, envolver 422 de FastAPI) → respetado, ningún task lo agrega.

**Placeholder scan:** sin TBD/TODO; todo paso de código trae el archivo completo o el bloque exacto a buscar/reemplazar, todo `Run:` trae comando y salida esperada.

**Type consistency:** `DomainError(message, code, category, details)` tiene la misma firma en Tasks 1 y 4 (mismo código, dos repos). Los 5 códigos de error de la Task 5 (`ACC-001/002`, `CAT-001/002`, `INV-001`) son los mismos que documenta la Task 7 en `LIBRERIA.md` — verificado cruzando ambas tablas. `ErrorCategory` los valores usados (`not_found`, `unauthorized`, `conflict`) están en el enum que define la Task 1/4, sin valores inventados fuera de ese set.
