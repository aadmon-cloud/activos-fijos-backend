# Stack

## Tecnologías principales

| Tech | Uso |
|---|---|
| Python 3.12 + FastAPI | API HTTP, inyección de dependencias con `Depends` |
| Motor (AsyncIO) | Driver async de MongoDB |
| Pydantic / pydantic-settings | Validación de schemas HTTP y configuración |
| Uvicorn / Gunicorn | Servidor ASGI (`gunicorn -k uvicorn.workers.UvicornWorker`) |
| pytest / pytest-asyncio | Tests unitarios |

## Integraciones externas incluidas en `shared/infrastructure`

Google Cloud Secret Manager, MongoDB (X.509 en la nube / sin TLS en local),
y llamadas autenticadas Cloud Run↔Cloud Run (`gcp/cloud_run/`, `gcp/authentication/`).

## Patrones clave de FastAPI

```python
# Annotated + Depends es el estandar del proyecto
async def mi_endpoint(
    body: MiRequest,
    service: Annotated[MiService, Depends(get_mi_service)],
) -> MiResponse:
    ...
```

## Motor — acceso a base de datos

**Patrón adoptado: singleton `mongo_manager`**, no `Depends(get_mongo_db)`. El
ciclo de vida de la conexión se maneja en `shared/bootstrap/application.py`
(`lifespan`), y cualquier repositorio accede a la base con:

```python
from shared.infrastructure.persistence.mongo.database import mongo_manager

class MongoXxxRepository(XxxRepositoryPort):
    @property
    def _collection(self):
        return mongo_manager.get_database()["nombre_coleccion"]
```

Con `ENTORNO=local` la conexión es directa (sin TLS/X.509), pensada para el
Mongo de `docker-compose.yml`. Con cualquier otro valor de `ENTORNO`, se
conecta con certificado X.509 obtenido de GCP Secret Manager.

## Pydantic — schemas HTTP vs entidades de dominio

- `infrastructure/api/schemas.py` → schemas HTTP (Pydantic, para FastAPI)
- `domain/entities.py` → entidades puras (dataclass, sin Pydantic)
- `application/dto/` → DTOs de transferencia entre capas (dataclass)

## Punto de entrada

`main.py` → `shared/bootstrap/application.py:create_app()` → `register_module(app)` por módulo.

## Arranque local

```bash
docker compose up -d mongo
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
copy .env.example .env
python main.py
```

Endpoints: `http://localhost:8080/docs`

## Variables de entorno necesarias

```
GCP_PROJECT_ID
GOOGLE_CLOUD_RUN_AUDIENCE   # opcional, solo si el servicio verifica tokens entrantes
ENTORNO                     # "local" para desarrollo, cualquier otro valor usa Secret Manager
SYSTEM_NAME                 # opcional
MONGO_URL
MONGO_DB
MONGO_CERT_SECRET_NAME      # obligatorio solo si ENTORNO != "local"
```

## Despliegue

Ver `cloudbuild.yaml` en la raíz del repo: corre `pytest` como gate, usa
`--cache-from` contra la imagen `:latest` previa para evitar reinstalar
dependencias en cambios de solo código, y despliega con `gcloud run deploy`.
