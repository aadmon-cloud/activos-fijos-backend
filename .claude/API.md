# API — Patrones HTTP

## Ruta estándar

```python
# modules/<modulo>/infrastructure/api/routes.py
router = APIRouter(prefix="/api/xxx", tags=["xxx"])

@router.post(
    "",
    status_code=201,
    summary="Crea un nuevo xxx",
    response_description="ID del recurso creado",
    responses={
        409: {"description": "Conflicto de negocio (p. ej. duplicado)"},
        422: {"description": "Datos de entrada inválidos"},
    },
)
async def crear_xxx(
    body: CrearXxxRequest,
    service: Annotated[CrearXxxService, Depends(get_crear_xxx_service)],
) -> XxxResponse:
    resultado = await service.ejecutar(CrearXxxDTO(...))
    return XxxResponse(...)
```

## Inyección de dependencias

```python
# modules/<modulo>/infrastructure/api/dependencies.py
def get_crear_xxx_service(
    db: Annotated[AsyncIOMotorDatabase, Depends(get_mongo_db)],
) -> CrearXxxService:
    return CrearXxxService(MongoXxxRepository(db))
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

Los schemas HTTP no son entidades de dominio ni DTOs de aplicación. Son la interfaz pública de la API.

## Registro del módulo

```python
# modules/<modulo>/bootstrap.py
def register_module(app: FastAPI) -> None:
    app.include_router(router)
```

Registrado en `shared/bootstrap/application.py`.

## Manejo de errores de dominio

Los errores de dominio (`DomainError`) deben capturarse en la capa HTTP y convertirse a respuestas HTTP apropiadas. No deben llegar al cliente como errores 500.
