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

Como las rutas ya no usan anotación de retorno `-> XxxResponse` ni
`response_model=`, el body de éxito queda **sin tipar** en el schema
OpenAPI/Swagger generado. `XxxResponse` sigue existiendo como fuente de
verdad del shape de `data` en el lado Python (se usa vía `.model_dump()` para
construirlo), pero ya no aparece como el response schema documentado del
endpoint en Swagger. Es un trade-off aceptado del patrón de dict inline, no
un descuido.

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

El envelope de `GEN-500` **no** incluye `category` ni `metadata` (a diferencia
de la respuesta de un `DomainError`) — ningún frontend debe asumir que todo
body con `status: "error"` trae el mismo set de claves.

Los errores `422` que arma FastAPI automáticamente (body/query no cumple el
schema Pydantic) **no** pasan por este envelope — quedan con el shape default
de FastAPI (`{"detail": [...]}`), distinto de un `DomainError` de categoría
`validation`.
