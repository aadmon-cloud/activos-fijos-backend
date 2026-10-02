# Stack

## Tecnologías principales

| Tech | Uso |
|---|---|
| Python + FastAPI | API HTTP, inyección de dependencias con `Depends` |
| Motor (AsyncIO) | Driver async de MongoDB |
| PyMongo | Driver sync (scripts, herramientas) |
| Pydantic | Validación y serialización de schemas HTTP |
| Uvicorn / Gunicorn | Servidor ASGI |
| pytest | Tests unitarios e integración |

## Integraciones externas (según proyecto)

Google Cloud (Secret Manager), Redis, MinIO — se agregan según necesidad del proyecto concreto.

## Patrones clave de FastAPI

```python
# Annotated + Depends es el estándar del proyecto
async def mi_endpoint(
    body: MiRequest,
    service: Annotated[MiService, Depends(get_mi_service)],
) -> MiResponse:
    ...
```

## Motor — acceso a base de datos

```python
# db llega por inyección, nunca como singleton global
class MongoXxxRepository(XxxRepositoryPort):
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["nombre_coleccion"]
```

## Pydantic — schemas HTTP vs entidades de dominio

- `infrastructure/api/schemas.py` → schemas HTTP (Pydantic, para FastAPI)
- `domain/entities/` → entidades puras (dataclass o clase simple, sin Pydantic)
- `application/dto/` → DTOs de transferencia entre capas (pueden ser Pydantic o dataclass)

## Punto de entrada

`main.py` → `shared/bootstrap/application.py` → `register_module(app)` por módulo.

## Arranque local

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Endpoints: `http://localhost:8080/docs`

## Variables de entorno necesarias

```
MONGO_URL
MONGO_DB
```

Variables adicionales (GCP, Redis, etc.) según las integraciones que use el proyecto.
