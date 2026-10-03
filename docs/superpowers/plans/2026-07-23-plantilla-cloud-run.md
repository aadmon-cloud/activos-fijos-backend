# Plantilla FastAPI/Cloud Run Hexagonal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el repo `fastapi-cloud-run` como plantilla base clonable para microservicios FastAPI en Cloud Run con arquitectura hexagonal, incluyendo un módulo de ejemplo funcional (`tareas`), infraestructura GCP compartida (Mongo, Secret Manager, auth Cloud Run↔Cloud Run), tests, `cloudbuild.yaml` con caché de capas, y la documentación `.claude/*.md` adaptada de `UltimateBackend`.

**Architecture:** Arquitectura hexagonal por módulo (`domain → application → infrastructure`), con `shared/` para infraestructura transversal (Mongo, GCP) y `bootstrap.py` por módulo que se registra en `shared/bootstrap/application.py`. El código de infraestructura compartida se porta y generaliza desde `ms-continuum` (proyecto real ya en producción con este patrón).

**Tech Stack:** FastAPI + Motor (async MongoDB) + Pydantic/pydantic-settings + Uvicorn/Gunicorn + pytest/pytest-asyncio. Despliegue: Docker + Cloud Build (`cloudbuild.yaml`) + Cloud Run.

## Global Constraints

- Runtime: Python 3.12 (imagen `python:3.12.8-slim-bookworm`, igual a `ms-continuum`).
- Sin `__init__.py` en ningún directorio de `modules/`/`shared/` (namespace packages de Python 3.3+), por convención de `CONVENTIONS.md`/`ARCHITECTURE.md`.
- Gestor de dependencias: `pip` + `requirements.txt`/`requirements-dev.txt` únicamente. Nada de poetry/uv/pipenv.
- Regla de dependencias entre capas: `infrastructure → application → domain`. `domain/` no importa FastAPI, Motor, Pydantic ni SDKs de GCP. `application/` no importa FastAPI ni Motor.
- Acceso a Mongo: patrón singleton `mongo_manager` (`shared/infrastructure/persistence/mongo/database.py`), consistente con el código real de `ms-continuum` — **no** el patrón `Depends(get_mongo_db)` que describía (aspiracionalmente, sin implementación real) la documentación original de `UltimateBackend`. Los `.md` de esta plantilla se adaptan para documentar el patrón realmente adoptado.
- Todo servicio de `application/` y toda entidad/error de `domain/` con lógica no trivial debe tener test unitario en `tests/unit/`, espejando el path del código con prefijo `test_`.
- Desarrollo local no depende de credenciales GCP reales: con `ENTORNO=local`, `database.py` conecta directo a Mongo (docker-compose) sin TLS/X.509 ni Secret Manager.
- Imagen Docker: `python:3.12.8-slim-bookworm`, `gunicorn` + `uvicorn.workers.UvicornWorker`, `PORT=8080`; orden de capas `COPY requirements.txt` + `pip install` antes de `COPY . .` (no alterar este orden — es lo que permite el caché de capas en `cloudbuild.yaml`).
- `cloudbuild.yaml` corre `pytest` como gate antes de construir/publicar la imagen, y usa `--cache-from` contra la imagen `:latest` previa.
- No se implementa en esta plantilla el framework de `MongoCollectionDefinition`/`registry.py`/`ConstructorPipelineBase`/script de sync de `UltimateBackend` — ver nota en Task 16 (`MONGODB.md`/`MONGODB_QUERIES.md`). Si un proyecto concreto lo necesita, se porta desde `ms-continuum` como adición deliberada.

---

## Task 1: Bootstrap del repo — config, dependencias, entorno de tests

**Files:**
- Create: `config/settings.py`
- Create: `config/logger.py`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `pytest.ini`
- Create: `tests/conftest.py`
- Test: `tests/unit/config/test_settings.py`

**Interfaces:**
- Produces: `config.settings.settings` (instancia de `Settings`, pydantic-settings) con campos `GCP_PROJECT_ID: str`, `GOOGLE_CLOUD_RUN_AUDIENCE: str | None`, `ENTORNO: str = "local"`, `SYSTEM_NAME: str | None`, `MONGO_URL: str`, `MONGO_DB: str`, `MONGO_CERT_SECRET_NAME: str | None`.
- Produces: `config.logger.configurar_logging(nivel: int = logging.INFO) -> None`.
- Produces: variables de entorno de test (`GCP_PROJECT_ID`, `ENTORNO=local`, `MONGO_URL`, `MONGO_DB`) seteadas por `tests/conftest.py` antes de que cualquier módulo importe `config.settings` — todas las tareas siguientes dependen de esto para que sus tests no fallen al importar `settings`.

- [ ] **Step 1: Crear `tests/conftest.py` con las variables de entorno mínimas para que `Settings()` no falle al importar**

```python
import os

os.environ.setdefault("GCP_PROJECT_ID", "test-project")
os.environ.setdefault("ENTORNO", "local")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "test_db")
```

- [ ] **Step 2: Escribir el test de `Settings` (fallará porque `config/settings.py` no existe)**

```python
# tests/unit/config/test_settings.py
from config.settings import Settings


def test_settings_usa_valores_por_defecto_cuando_no_se_especifican():
    settings = Settings(
        GCP_PROJECT_ID="proyecto-x",
        MONGO_URL="mongodb://localhost:27017",
        MONGO_DB="mi_db",
    )
    assert settings.ENTORNO == "local"
    assert settings.MONGO_CERT_SECRET_NAME is None
    assert settings.GOOGLE_CLOUD_RUN_AUDIENCE is None


def test_settings_lee_variables_de_entorno(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "proyecto-y")
    monkeypatch.setenv("MONGO_URL", "mongodb://otra:27017")
    monkeypatch.setenv("MONGO_DB", "otra_db")
    monkeypatch.setenv("ENTORNO", "cloud")

    settings = Settings()

    assert settings.GCP_PROJECT_ID == "proyecto-y"
    assert settings.ENTORNO == "cloud"
```

- [ ] **Step 3: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/config/test_settings.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'config'` (o similar, `config/settings.py` no existe)

- [ ] **Step 4: Crear `config/settings.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GCP_PROJECT_ID: str
    GOOGLE_CLOUD_RUN_AUDIENCE: str | None = None
    ENTORNO: str = "local"
    SYSTEM_NAME: str | None = None

    MONGO_URL: str
    MONGO_DB: str
    MONGO_CERT_SECRET_NAME: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
```

- [ ] **Step 5: Crear `config/logger.py`**

```python
import logging


def configurar_logging(nivel: int = logging.INFO) -> None:
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
```

- [ ] **Step 6: Crear `pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 7: Crear `requirements.txt`**

```
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.12.1
certifi==2026.1.4
cffi==2.0.0
charset-normalizer==3.4.4
click==8.3.1
colorama==0.4.6
cryptography==46.0.5
dnspython==2.8.0
email-validator==2.3.0
fastapi==0.129.0
google-api-core==2.29.0
google-auth==2.48.0
google-cloud-secret-manager==2.26.0
googleapis-common-protos==1.72.0
greenlet==3.3.1
grpc-google-iam-v1==0.14.3
grpcio==1.78.0
grpcio-status==1.78.0
gunicorn==23.0.0
h11==0.16.0
httpcore==1.0.9
httpx==0.28.1
idna==3.11
motor==3.7.1
proto-plus==1.27.1
protobuf==6.33.5
pyasn1==0.6.2
pyasn1_modules==0.4.2
pycparser==3.0
pydantic==2.12.5
pydantic-settings==2.13.0
pydantic_core==2.41.5
pymongo==4.16.0
python-dotenv==1.2.1
python-multipart==0.0.22
requests==2.32.5
rsa==4.9.1
starlette==0.52.1
typing_extensions==4.15.0
tzdata==2026.1
urllib3==2.6.3
uvicorn==0.40.0
watchfiles==1.1.1
```

- [ ] **Step 8: Crear `requirements-dev.txt`**

```
-r requirements.txt
pytest==8.3.4
pytest-asyncio==0.25.2
```

- [ ] **Step 9: Crear `.env.example`**

```
GCP_PROJECT_ID=
GOOGLE_CLOUD_RUN_AUDIENCE=
ENTORNO=local
SYSTEM_NAME=fastapi-cloud-run-template

MONGO_URL=mongodb://localhost:27017
MONGO_DB=fastapi_cloud_run_template
MONGO_CERT_SECRET_NAME=
```

- [ ] **Step 10: Crear `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
.pytest_cache/
.coverage
htmlcov/
```

- [ ] **Step 11: Ejecutar el test y confirmar que pasa**

Run: `pytest tests/unit/config/test_settings.py -v`
Expected: PASS (2 tests)

- [ ] **Step 12: Commit**

```bash
git add config/ requirements.txt requirements-dev.txt .env.example .gitignore pytest.ini tests/conftest.py tests/unit/config/test_settings.py
git commit -m "feat: bootstrap config, dependencias y entorno de tests"
```

---

## Task 2: Dominio compartido — `BaseDomainEntity` y `DomainError`

**Files:**
- Create: `shared/domain/entities/base.py`
- Create: `shared/domain/errors.py`
- Test: `tests/unit/shared/domain/test_errors.py`

**Interfaces:**
- Produces: `shared.domain.entities.base.BaseDomainEntity` — dataclass base, frozen, `kw_only=True`.
- Produces: `shared.domain.errors.DomainError` — `Exception` con atributo de clase `status_code: int = 400` y atributo de instancia `mensaje: str`.

- [ ] **Step 1: Escribir el test de `DomainError`**

```python
# tests/unit/shared/domain/test_errors.py
from shared.domain.errors import DomainError


def test_domain_error_expone_mensaje_y_status_code_por_defecto():
    error = DomainError("algo salio mal")

    assert str(error) == "algo salio mal"
    assert error.mensaje == "algo salio mal"
    assert error.status_code == 400


def test_domain_error_permite_status_code_personalizado_en_subclase():
    class MiErrorDeNegocio(DomainError):
        status_code = 409

    error = MiErrorDeNegocio("conflicto")

    assert error.status_code == 409
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/shared/domain/test_errors.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'shared'`

- [ ] **Step 3: Crear `shared/domain/entities/base.py`**

```python
from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class BaseDomainEntity:
    """Base para entidades de dominio puras, sin dependencias externas."""
```

- [ ] **Step 4: Crear `shared/domain/errors.py`**

```python
class DomainError(Exception):
    """Excepcion base para errores de reglas de negocio."""

    status_code: int = 400

    def __init__(self, mensaje: str):
        super().__init__(mensaje)
        self.mensaje = mensaje
```

- [ ] **Step 5: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/shared/domain/test_errors.py -v`
Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add shared/domain/entities/base.py shared/domain/errors.py tests/unit/shared/domain/test_errors.py
git commit -m "feat: agregar BaseDomainEntity y DomainError compartidos"
```

---

## Task 3: Manejo de errores HTTP — `error_handlers.py`

**Files:**
- Create: `shared/infrastructure/api/error_handlers.py`
- Test: `tests/unit/shared/infrastructure/api/test_error_handlers.py`

**Interfaces:**
- Consumes: `shared.domain.errors.DomainError` (Task 2).
- Produces: `shared.infrastructure.api.error_handlers.register_error_handlers(app: FastAPI) -> None` — registra un exception handler que convierte cualquier `DomainError` en `JSONResponse(status_code=exc.status_code, content={"detail": exc.mensaje})`.

- [ ] **Step 1: Escribir el test usando una app FastAPI de prueba**

```python
# tests/unit/shared/infrastructure/api/test_error_handlers.py
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.domain.errors import DomainError
from shared.infrastructure.api.error_handlers import register_error_handlers


class ErrorDePrueba(DomainError):
    status_code = 409


def _crear_app_de_prueba() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/falla")
    async def falla():
        raise ErrorDePrueba("recurso duplicado")

    return app


def test_domain_error_se_convierte_en_respuesta_json_con_su_status_code():
    cliente = TestClient(_crear_app_de_prueba())

    respuesta = cliente.get("/falla")

    assert respuesta.status_code == 409
    assert respuesta.json() == {"detail": "recurso duplicado"}
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/shared/infrastructure/api/test_error_handlers.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'shared.infrastructure.api.error_handlers'`

- [ ] **Step 3: Crear `shared/infrastructure/api/error_handlers.py`**

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.domain.errors import DomainError


async def _manejar_domain_error(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.mensaje})


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _manejar_domain_error)
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/shared/infrastructure/api/test_error_handlers.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add shared/infrastructure/api/error_handlers.py tests/unit/shared/infrastructure/api/test_error_handlers.py
git commit -m "feat: convertir DomainError en respuestas HTTP"
```

---

## Task 4: Secret Manager helper

**Files:**
- Create: `shared/infrastructure/gcp/secret_manager.py`
- Test: `tests/unit/shared/infrastructure/gcp/test_secret_manager.py`

**Interfaces:**
- Produces: `shared.infrastructure.gcp.secret_manager.GestorSecretosGCP(id_proyecto: str)` con método `obtener_secreto(id_secreto: str, id_version: str = "latest", reintentos: int = 3, retraso: int = 5) -> str`.
- Produces: `shared.infrastructure.gcp.secret_manager.ErrorRecuperacionSecreto(Exception)`.

Portado tal cual desde `ms-continuum` (`shared/infrastructure/gcp/secret_manager.py`) — es genérico, sin referencias de negocio.

- [ ] **Step 1: Escribir tests mockeando el cliente de Secret Manager**

```python
# tests/unit/shared/infrastructure/gcp/test_secret_manager.py
from unittest.mock import MagicMock, patch

import pytest
from google.api_core.exceptions import NotFound, PermissionDenied

from shared.infrastructure.gcp.secret_manager import (
    ErrorRecuperacionSecreto,
    GestorSecretosGCP,
)


def _respuesta_falsa(valor: str) -> MagicMock:
    respuesta = MagicMock()
    respuesta.payload.data.decode.return_value = valor
    return respuesta


@patch("shared.infrastructure.gcp.secret_manager.secretmanager.SecretManagerServiceClient")
def test_obtener_secreto_retorna_el_valor_decodificado(cliente_mock_cls):
    cliente_mock_cls.return_value.access_secret_version.return_value = _respuesta_falsa("valor-secreto")

    gestor = GestorSecretosGCP("mi-proyecto")
    valor = gestor.obtener_secreto("mi-secreto")

    assert valor == "valor-secreto"


@patch("shared.infrastructure.gcp.secret_manager.secretmanager.SecretManagerServiceClient")
def test_obtener_secreto_lanza_error_propio_si_no_existe(cliente_mock_cls):
    cliente_mock_cls.return_value.access_secret_version.side_effect = NotFound("no existe")

    gestor = GestorSecretosGCP("mi-proyecto")

    with pytest.raises(ErrorRecuperacionSecreto):
        gestor.obtener_secreto("no-existe")


@patch("shared.infrastructure.gcp.secret_manager.secretmanager.SecretManagerServiceClient")
def test_obtener_secreto_lanza_error_propio_si_no_hay_permisos(cliente_mock_cls):
    cliente_mock_cls.return_value.access_secret_version.side_effect = PermissionDenied("sin permiso")

    gestor = GestorSecretosGCP("mi-proyecto")

    with pytest.raises(ErrorRecuperacionSecreto):
        gestor.obtener_secreto("sin-permiso")
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/shared/infrastructure/gcp/test_secret_manager.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'shared.infrastructure.gcp.secret_manager'`

- [ ] **Step 3: Crear `shared/infrastructure/gcp/secret_manager.py`**

```python
import logging
import time

from google.api_core.exceptions import GoogleAPICallError, NotFound, PermissionDenied
from google.cloud import secretmanager

logger = logging.getLogger(__name__)


class ErrorRecuperacionSecreto(Exception):
    """Raised when a secret cannot be fetched from GCP Secret Manager."""


class GestorSecretosGCP:
    def __init__(self, id_proyecto: str):
        self._cliente = secretmanager.SecretManagerServiceClient()
        self._id_proyecto = id_proyecto

    def obtener_secreto(
        self,
        id_secreto: str,
        id_version: str = "latest",
        reintentos: int = 3,
        retraso: int = 5,
    ) -> str:
        nombre_secreto = (
            f"projects/{self._id_proyecto}/secrets/{id_secreto}/versions/{id_version}"
        )

        for intento in range(reintentos):
            try:
                respuesta = self._cliente.access_secret_version(
                    request={"name": nombre_secreto}
                )
                return respuesta.payload.data.decode("UTF-8")
            except NotFound as exc:
                raise ErrorRecuperacionSecreto(
                    f"El secreto '{id_secreto}' no existe en GCP."
                ) from exc
            except PermissionDenied as exc:
                raise ErrorRecuperacionSecreto(
                    f"No hay permisos para leer el secreto '{id_secreto}'."
                ) from exc
            except GoogleAPICallError as exc:
                if intento < reintentos - 1:
                    logger.warning(
                        "Intento %s fallido leyendo '%s'. Reintentando en %ss.",
                        intento + 1,
                        id_secreto,
                        retraso,
                    )
                    time.sleep(retraso)
                    continue

                raise ErrorRecuperacionSecreto(
                    f"Fallo tras {reintentos} intentos para '{id_secreto}': {exc.message}"
                ) from exc
            except Exception as exc:
                raise ErrorRecuperacionSecreto(
                    f"Error inesperado en Secret Manager: {exc}"
                ) from exc
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/shared/infrastructure/gcp/test_secret_manager.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add shared/infrastructure/gcp/secret_manager.py tests/unit/shared/infrastructure/gcp/test_secret_manager.py
git commit -m "feat: portar GestorSecretosGCP desde ms-continuum"
```

---

## Task 5: Cliente Mongo dual-mode (local / GCP)

**Files:**
- Create: `shared/infrastructure/persistence/mongo/database.py`
- Test: `tests/unit/shared/infrastructure/persistence/mongo/test_database.py`

**Interfaces:**
- Consumes: `shared.infrastructure.gcp.secret_manager.GestorSecretosGCP` (Task 4), `config.settings.settings` (Task 1).
- Produces: `shared.infrastructure.persistence.mongo.database.DatabaseManager` con métodos `connect()`, `close()`, `get_database()`, y atributo `client`.
- Produces: `shared.infrastructure.persistence.mongo.database.mongo_manager` — instancia singleton de `DatabaseManager`, usada por todos los repositorios Mongo de los módulos.

- [ ] **Step 1: Escribir tests para ambos modos de conexión**

```python
# tests/unit/shared/infrastructure/persistence/mongo/test_database.py
import os
from unittest.mock import MagicMock, patch

from shared.infrastructure.persistence.mongo.database import DatabaseManager


@patch("shared.infrastructure.persistence.mongo.database.AsyncIOMotorClient")
def test_connect_en_modo_local_no_usa_tls_ni_secret_manager(cliente_mock_cls, monkeypatch):
    monkeypatch.setenv("ENTORNO", "local")
    from config.settings import Settings

    with patch("shared.infrastructure.persistence.mongo.database.settings", Settings()):
        manager = DatabaseManager()
        manager.connect()

    _, kwargs = cliente_mock_cls.call_args
    assert "tls" not in kwargs
    assert "tlsCertificateKeyFile" not in kwargs
    manager.close()


@patch("shared.infrastructure.persistence.mongo.database.AsyncIOMotorClient")
@patch("shared.infrastructure.persistence.mongo.database.GestorSecretosGCP")
def test_connect_en_modo_cloud_usa_certificado_de_secret_manager(
    gestor_mock_cls, cliente_mock_cls, monkeypatch
):
    monkeypatch.setenv("ENTORNO", "cloud")
    monkeypatch.setenv("MONGO_CERT_SECRET_NAME", "cert-mongo")
    from config.settings import Settings

    gestor_mock_cls.return_value.obtener_secreto.return_value = "contenido-certificado"

    with patch(
        "shared.infrastructure.persistence.mongo.database.settings",
        Settings(),
    ):
        manager = DatabaseManager()
        manager.connect()

        _, kwargs = cliente_mock_cls.call_args
        assert kwargs["tls"] is True
        assert kwargs["authMechanism"] == "MONGODB-X509"
        assert os.path.exists(kwargs["tlsCertificateKeyFile"])

        manager.close()

    assert manager.client is None


def test_connect_es_idempotente_si_ya_hay_cliente():
    manager = DatabaseManager()
    cliente_falso = MagicMock()
    manager.client = cliente_falso

    manager.connect()

    assert manager.client is cliente_falso
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/shared/infrastructure/persistence/mongo/test_database.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'shared.infrastructure.persistence.mongo.database'`

- [ ] **Step 3: Crear `shared/infrastructure/persistence/mongo/database.py`**

```python
import logging
import os
import tempfile
from datetime import UTC

from motor.motor_asyncio import AsyncIOMotorClient

from config.settings import settings
from shared.infrastructure.gcp.secret_manager import GestorSecretosGCP

logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self) -> None:
        self.client: AsyncIOMotorClient | None = None
        self.db_name: str = settings.MONGO_DB
        self._temp_cert_path: str | None = None

    def connect(self) -> None:
        if self.client:
            return

        if settings.ENTORNO == "local":
            self._conectar_local()
        else:
            self._conectar_con_certificado_gcp()

    def _conectar_local(self) -> None:
        logger.info("Conectando a MongoDB local (ENTORNO=local, sin TLS/X.509).")
        self.client = AsyncIOMotorClient(
            settings.MONGO_URL,
            tz_aware=True,
            tzinfo=UTC,
            uuidRepresentation="standard",
            serverSelectionTimeoutMS=5000,
        )

    def _conectar_con_certificado_gcp(self) -> None:
        logger.info("Iniciando conexion segura a MongoDB con X.509.")

        if not settings.MONGO_CERT_SECRET_NAME:
            raise ValueError(
                "MONGO_CERT_SECRET_NAME es obligatorio cuando ENTORNO != 'local'."
            )

        try:
            gestor_secretos = GestorSecretosGCP(settings.GCP_PROJECT_ID)
            contenido_certificado = gestor_secretos.obtener_secreto(
                settings.MONGO_CERT_SECRET_NAME
            )

            if not contenido_certificado:
                raise ValueError("El secreto del certificado de Mongo esta vacio.")

            temp_file = tempfile.NamedTemporaryFile(
                suffix=".pem", mode="w", delete=False
            )
            temp_file.write(contenido_certificado)
            temp_file.close()
            self._temp_cert_path = temp_file.name

            self.client = AsyncIOMotorClient(
                settings.MONGO_URL,
                tls=True,
                tlsCertificateKeyFile=self._temp_cert_path,
                authMechanism="MONGODB-X509",
                maxPoolSize=100,
                minPoolSize=10,
                tz_aware=True,
                tzinfo=UTC,
                uuidRepresentation="standard",
                serverSelectionTimeoutMS=5000,
            )
            logger.info("Conexion establecida a MongoDB: %s", self.db_name)
        except Exception:
            if self._temp_cert_path and os.path.exists(self._temp_cert_path):
                os.remove(self._temp_cert_path)
            raise

    def close(self) -> None:
        if self.client:
            self.client.close()
            self.client = None

        if self._temp_cert_path and os.path.exists(self._temp_cert_path):
            os.remove(self._temp_cert_path)
            self._temp_cert_path = None

    def get_database(self):
        return self.client[self.db_name]


mongo_manager = DatabaseManager()
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/shared/infrastructure/persistence/mongo/test_database.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add shared/infrastructure/persistence/mongo/database.py tests/unit/shared/infrastructure/persistence/mongo/test_database.py
git commit -m "feat: cliente Mongo dual-mode local/GCP con singleton mongo_manager"
```

---

## Task 6: Contratos de invocación de servicios + resolver Cloud Run

**Files:**
- Create: `shared/application/service_invocation/dto.py`
- Create: `shared/application/service_invocation/ports.py`
- Create: `shared/application/service_invocation/exceptions.py`
- Create: `shared/infrastructure/gcp/cloud_run/resolver.py`
- Test: `tests/unit/shared/infrastructure/gcp/cloud_run/test_resolver.py`

**Interfaces:**
- Consumes: `shared.infrastructure.gcp.secret_manager.GestorSecretosGCP` (Task 4).
- Produces: `ConfiguracionServicioExterno(nombre, url_base, audiencia_resuelta=None, requiere_autenticacion=True, cabeceras_extra={}, tiempo_espera_segundos=10.0)` (dataclass).
- Produces: `SolicitudServicioExterno(ruta, metodo="GET", cuerpo_json=None, parametros_query=None, cabeceras={}, tiempo_espera_segundos=None)` (dataclass).
- Produces: ABCs `IInvocadorServicio.invocar(nombre_servicio, solicitud)`, `IResolutorServicioExterno.resolver(nombre_servicio) -> ConfiguracionServicioExterno`, `IProveedorTokenServicio.obtener_token(audiencia) -> str`.
- Produces: `ErrorInvocacionServicioExterno`, `ErrorAutenticacionServicioExterno`, `ErrorServicioExternoNoConfigurado`.
- Produces: `ResolutorServicioCloudRun(id_proyecto: str)` implementando `IResolutorServicioExterno`, usado por Task 7.

- [ ] **Step 1: Escribir tests del resolver**

```python
# tests/unit/shared/infrastructure/gcp/cloud_run/test_resolver.py
from unittest.mock import patch

import pytest

from shared.application.service_invocation.exceptions import (
    ErrorServicioExternoNoConfigurado,
)
from shared.infrastructure.gcp.cloud_run.resolver import ResolutorServicioCloudRun


def test_resolver_usa_url_directa_de_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("CLOUD_RUN_FACTURACION_URL", "https://facturacion.example.com")

    resolutor = ResolutorServicioCloudRun("mi-proyecto")
    config = resolutor.resolver("facturacion")

    assert config.url_base == "https://facturacion.example.com"


@patch("shared.infrastructure.gcp.cloud_run.resolver.GestorSecretosGCP")
def test_resolver_usa_secret_manager_y_cachea_el_resultado(gestor_mock_cls, monkeypatch):
    monkeypatch.setenv(
        "CLOUD_RUN_FACTURACION_URL_SECRET_NAME", "url-facturacion"
    )
    gestor_mock_cls.return_value.obtener_secreto.return_value = "https://facturacion.example.com"

    resolutor = ResolutorServicioCloudRun("mi-proyecto")
    config_1 = resolutor.resolver("facturacion")
    config_2 = resolutor.resolver("facturacion")

    assert config_1.url_base == "https://facturacion.example.com"
    assert config_2.url_base == "https://facturacion.example.com"
    gestor_mock_cls.return_value.obtener_secreto.assert_called_once()


def test_resolver_lanza_error_si_no_esta_configurado():
    resolutor = ResolutorServicioCloudRun("mi-proyecto")

    with pytest.raises(ErrorServicioExternoNoConfigurado):
        resolutor.resolver("servicio-inexistente")
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/shared/infrastructure/gcp/cloud_run/test_resolver.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'shared.application.service_invocation'`

- [ ] **Step 3: Crear `shared/application/service_invocation/dto.py`**

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConfiguracionServicioExterno:
    nombre: str
    url_base: str
    audiencia_resuelta: str | None = None
    requiere_autenticacion: bool = True
    cabeceras_extra: dict[str, str] = field(default_factory=dict)
    tiempo_espera_segundos: float = 10.0


@dataclass
class SolicitudServicioExterno:
    ruta: str
    metodo: str = "GET"
    cuerpo_json: Any | None = None
    parametros_query: dict[str, Any] | None = None
    cabeceras: dict[str, str] = field(default_factory=dict)
    tiempo_espera_segundos: float | None = None
```

- [ ] **Step 4: Crear `shared/application/service_invocation/ports.py`**

```python
from abc import ABC, abstractmethod
from typing import Any

from shared.application.service_invocation.dto import (
    ConfiguracionServicioExterno,
    SolicitudServicioExterno,
)


class IInvocadorServicio(ABC):
    @abstractmethod
    def invocar(self, nombre_servicio: str, solicitud: SolicitudServicioExterno) -> Any: ...


class IResolutorServicioExterno(ABC):
    @abstractmethod
    def resolver(self, nombre_servicio: str) -> ConfiguracionServicioExterno: ...


class IProveedorTokenServicio(ABC):
    @abstractmethod
    def obtener_token(self, audiencia: str) -> str: ...
```

- [ ] **Step 5: Crear `shared/application/service_invocation/exceptions.py`**

```python
class ErrorInvocacionServicioExterno(Exception):
    def __init__(self, nombre_servicio: str, detalle: str, status_code: int | None = None):
        super().__init__(f"Error invocando '{nombre_servicio}': {detalle}")
        self.nombre_servicio = nombre_servicio
        self.detalle = detalle
        self.status_code = status_code


class ErrorAutenticacionServicioExterno(Exception):
    def __init__(self, nombre_servicio: str, detalle: str):
        super().__init__(f"Error de autenticacion invocando '{nombre_servicio}': {detalle}")
        self.nombre_servicio = nombre_servicio
        self.detalle = detalle


class ErrorServicioExternoNoConfigurado(Exception):
    def __init__(self, nombre_servicio: str):
        super().__init__(f"El servicio '{nombre_servicio}' no esta configurado.")
        self.nombre_servicio = nombre_servicio
```

- [ ] **Step 6: Crear `shared/infrastructure/gcp/cloud_run/resolver.py`**

```python
import os

from shared.application.service_invocation.dto import ConfiguracionServicioExterno
from shared.application.service_invocation.exceptions import (
    ErrorServicioExternoNoConfigurado,
)
from shared.application.service_invocation.ports import IResolutorServicioExterno
from shared.infrastructure.gcp.secret_manager import GestorSecretosGCP


class ResolutorServicioCloudRun(IResolutorServicioExterno):
    def __init__(self, id_proyecto: str):
        self._gestor_secretos = GestorSecretosGCP(id_proyecto)
        self._cache: dict[str, ConfiguracionServicioExterno] = {}

    def resolver(self, nombre_servicio: str) -> ConfiguracionServicioExterno:
        nombre_normalizado = self._normalizar_nombre_servicio(nombre_servicio)

        if nombre_normalizado in self._cache:
            return self._cache[nombre_normalizado]

        url_base = self._resolver_url_directa(nombre_normalizado)
        if not url_base:
            nombre_secreto = self._resolver_nombre_secreto(nombre_normalizado)
            if nombre_secreto:
                url_base = self._gestor_secretos.obtener_secreto(nombre_secreto)

        if not url_base:
            raise ErrorServicioExternoNoConfigurado(nombre_servicio)

        configuracion = ConfiguracionServicioExterno(
            nombre=nombre_servicio,
            url_base=url_base.rstrip("/"),
        )
        self._cache[nombre_normalizado] = configuracion
        return configuracion

    @staticmethod
    def _normalizar_nombre_servicio(nombre_servicio: str) -> str:
        return nombre_servicio.strip().upper().replace("-", "_")

    @staticmethod
    def _resolver_url_directa(nombre_normalizado: str) -> str | None:
        variables_entorno = [
            f"CLOUD_RUN_{nombre_normalizado}_URL",
            f"CLOUD_RUN_URL_{nombre_normalizado}",
        ]
        for variable_entorno in variables_entorno:
            valor = os.getenv(variable_entorno)
            if valor:
                return valor
        return None

    @staticmethod
    def _resolver_nombre_secreto(nombre_normalizado: str) -> str | None:
        variables_entorno = [
            f"CLOUD_RUN_{nombre_normalizado}_URL_SECRET_NAME",
            f"CLOUD_RUN_URL_{nombre_normalizado}_NAME",
        ]
        for variable_entorno in variables_entorno:
            valor = os.getenv(variable_entorno)
            if valor:
                return valor
        return None
```

- [ ] **Step 7: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/shared/infrastructure/gcp/cloud_run/test_resolver.py -v`
Expected: PASS (3 tests)

- [ ] **Step 8: Commit**

```bash
git add shared/application/service_invocation/ shared/infrastructure/gcp/cloud_run/resolver.py tests/unit/shared/infrastructure/gcp/cloud_run/test_resolver.py
git commit -m "feat: contratos de invocacion de servicios y resolver Cloud Run"
```

---

## Task 7: Proveedor de token + cliente saliente Cloud Run↔Cloud Run

**Files:**
- Create: `shared/infrastructure/gcp/cloud_run/token_provider.py`
- Create: `shared/infrastructure/gcp/cloud_run/client.py`
- Test: `tests/unit/shared/infrastructure/gcp/cloud_run/test_token_provider.py`
- Test: `tests/unit/shared/infrastructure/gcp/cloud_run/test_client.py`

**Interfaces:**
- Consumes: `IProveedorTokenServicio`, `IResolutorServicioExterno`, `ConfiguracionServicioExterno`, `SolicitudServicioExterno`, excepciones de Task 6.
- Produces: `ProveedorTokenCloudRunGoogle` implementando `IProveedorTokenServicio`.
- Produces: `ClienteCloudRun(resolutor, proveedor_token, nombre_sistema=None, correo_debug=None, sesion=None)` implementando `IInvocadorServicio.invocar(nombre_servicio, solicitud) -> Any`.

- [ ] **Step 1: Escribir el test del proveedor de token**

```python
# tests/unit/shared/infrastructure/gcp/cloud_run/test_token_provider.py
from unittest.mock import patch

from shared.infrastructure.gcp.cloud_run.token_provider import (
    ProveedorTokenCloudRunGoogle,
)


@patch("shared.infrastructure.gcp.cloud_run.token_provider.google.oauth2.id_token.fetch_id_token")
def test_obtener_token_delega_en_fetch_id_token(fetch_id_token_mock):
    fetch_id_token_mock.return_value = "token-falso"

    proveedor = ProveedorTokenCloudRunGoogle()
    token = proveedor.obtener_token("https://mi-servicio.example.com")

    assert token == "token-falso"
    fetch_id_token_mock.assert_called_once()
    assert fetch_id_token_mock.call_args.kwargs["audience"] == "https://mi-servicio.example.com"
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/shared/infrastructure/gcp/cloud_run/test_token_provider.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 3: Crear `shared/infrastructure/gcp/cloud_run/token_provider.py`**

```python
import google.auth.transport.requests
import google.oauth2.id_token

from shared.application.service_invocation.ports import IProveedorTokenServicio


class ProveedorTokenCloudRunGoogle(IProveedorTokenServicio):
    def __init__(self):
        self._solicitud_autenticacion = google.auth.transport.requests.Request()

    def obtener_token(self, audiencia: str) -> str:
        return google.oauth2.id_token.fetch_id_token(
            self._solicitud_autenticacion,
            audience=audiencia,
        )
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/shared/infrastructure/gcp/cloud_run/test_token_provider.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Escribir los tests del cliente saliente, con resolutor/proveedor/sesion falsos**

```python
# tests/unit/shared/infrastructure/gcp/cloud_run/test_client.py
from unittest.mock import MagicMock

import pytest

from shared.application.service_invocation.dto import (
    ConfiguracionServicioExterno,
    SolicitudServicioExterno,
)
from shared.application.service_invocation.exceptions import (
    ErrorInvocacionServicioExterno,
)
from shared.infrastructure.gcp.cloud_run.client import ClienteCloudRun


class _ResolutorFalso:
    def __init__(self, configuracion: ConfiguracionServicioExterno):
        self._configuracion = configuracion

    def resolver(self, nombre_servicio: str) -> ConfiguracionServicioExterno:
        return self._configuracion


class _ProveedorTokenFalso:
    def obtener_token(self, audiencia: str) -> str:
        return "token-de-prueba"


def _respuesta_falsa(status_code=200, json_data=None, ok=True):
    respuesta = MagicMock()
    respuesta.ok = ok
    respuesta.status_code = status_code
    respuesta.content = b"{}"
    respuesta.headers = {"Content-Type": "application/json"}
    respuesta.json.return_value = json_data or {}
    return respuesta


def test_invocar_agrega_bearer_token_cuando_requiere_autenticacion():
    sesion_falsa = MagicMock()
    sesion_falsa.request.return_value = _respuesta_falsa(json_data={"ok": True})

    configuracion = ConfiguracionServicioExterno(
        nombre="facturacion",
        url_base="https://facturacion.example.com",
        audiencia_resuelta="https://facturacion.example.com",
        requiere_autenticacion=True,
    )
    cliente = ClienteCloudRun(
        resolutor=_ResolutorFalso(configuracion),
        proveedor_token=_ProveedorTokenFalso(),
        sesion=sesion_falsa,
    )

    resultado = cliente.invocar("facturacion", SolicitudServicioExterno(ruta="/api/facturas"))

    assert resultado == {"ok": True}
    cabeceras_enviadas = sesion_falsa.request.call_args.kwargs["headers"]
    assert cabeceras_enviadas["Authorization"] == "Bearer token-de-prueba"


def test_invocar_lanza_error_propio_si_la_respuesta_no_es_ok():
    sesion_falsa = MagicMock()
    sesion_falsa.request.return_value = _respuesta_falsa(status_code=500, ok=False)

    configuracion = ConfiguracionServicioExterno(
        nombre="facturacion",
        url_base="https://facturacion.example.com",
        requiere_autenticacion=False,
    )
    cliente = ClienteCloudRun(
        resolutor=_ResolutorFalso(configuracion),
        proveedor_token=_ProveedorTokenFalso(),
        sesion=sesion_falsa,
    )

    with pytest.raises(ErrorInvocacionServicioExterno):
        cliente.invocar("facturacion", SolicitudServicioExterno(ruta="/api/facturas"))
```

- [ ] **Step 6: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/shared/infrastructure/gcp/cloud_run/test_client.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'shared.infrastructure.gcp.cloud_run.client'`

- [ ] **Step 7: Crear `shared/infrastructure/gcp/cloud_run/client.py`**

```python
import logging
from typing import Any
from urllib.parse import urljoin

import google.auth.exceptions
import requests

from shared.application.service_invocation.dto import (
    ConfiguracionServicioExterno,
    SolicitudServicioExterno,
)
from shared.application.service_invocation.exceptions import (
    ErrorAutenticacionServicioExterno,
    ErrorInvocacionServicioExterno,
)
from shared.application.service_invocation.ports import (
    IInvocadorServicio,
    IProveedorTokenServicio,
    IResolutorServicioExterno,
)

logger = logging.getLogger(__name__)


class ClienteCloudRun(IInvocadorServicio):
    def __init__(
        self,
        resolutor: IResolutorServicioExterno,
        proveedor_token: IProveedorTokenServicio,
        nombre_sistema: str | None = None,
        correo_debug: str | None = None,
        sesion: requests.Session | None = None,
    ):
        self._resolutor = resolutor
        self._proveedor_token = proveedor_token
        self._nombre_sistema = nombre_sistema
        self._correo_debug = correo_debug
        self._sesion = sesion or requests.Session()

    def invocar(self, nombre_servicio: str, solicitud: SolicitudServicioExterno) -> Any:
        configuracion_servicio = self._resolutor.resolver(nombre_servicio)
        url = self._construir_url(configuracion_servicio.url_base, solicitud.ruta)
        cabeceras = self._construir_cabeceras(
            nombre_servicio,
            configuracion_servicio,
            solicitud.cabeceras,
        )
        tiempo_espera = (
            solicitud.tiempo_espera_segundos
            or configuracion_servicio.tiempo_espera_segundos
        )

        try:
            respuesta = self._sesion.request(
                method=solicitud.metodo,
                url=url,
                headers=cabeceras,
                json=solicitud.cuerpo_json,
                params=solicitud.parametros_query,
                timeout=tiempo_espera,
            )
        except requests.RequestException as exc:
            raise ErrorInvocacionServicioExterno(
                nombre_servicio=nombre_servicio,
                detalle=str(exc),
            ) from exc

        if not respuesta.ok:
            raise ErrorInvocacionServicioExterno(
                nombre_servicio=nombre_servicio,
                detalle=self._extraer_detalle_error(respuesta),
                status_code=respuesta.status_code,
            )

        return self._parsear_respuesta(respuesta)

    def _construir_cabeceras(
        self,
        nombre_servicio: str,
        configuracion_servicio: ConfiguracionServicioExterno,
        cabeceras_solicitud: dict[str, str],
    ) -> dict[str, str]:
        cabeceras = dict(configuracion_servicio.cabeceras_extra)

        if configuracion_servicio.requiere_autenticacion:
            try:
                token = self._proveedor_token.obtener_token(
                    configuracion_servicio.audiencia_resuelta
                )
            except google.auth.exceptions.GoogleAuthError as exc:
                raise ErrorAutenticacionServicioExterno(
                    nombre_servicio,
                    str(exc),
                ) from exc

            cabeceras["Authorization"] = f"Bearer {token}"

        if self._nombre_sistema:
            cabeceras["X-Sistema"] = self._nombre_sistema

        if self._correo_debug:
            cabeceras["X-Debug-Email"] = self._correo_debug

        cabeceras.update(cabeceras_solicitud)
        return {llave: valor for llave, valor in cabeceras.items() if valor}

    @staticmethod
    def _construir_url(url_base: str, ruta: str) -> str:
        url_base_normalizada = f"{url_base.rstrip('/')}/"
        ruta_normalizada = ruta.lstrip("/")
        return urljoin(url_base_normalizada, ruta_normalizada)

    @staticmethod
    def _extraer_detalle_error(respuesta: requests.Response) -> Any:
        try:
            carga_error = respuesta.json()
        except ValueError:
            return respuesta.text

        if isinstance(carga_error, dict):
            return (
                carga_error.get("detail")
                or carga_error.get("message")
                or carga_error.get("error")
                or respuesta.text
            )
        return str(carga_error)

    @staticmethod
    def _parsear_respuesta(respuesta: requests.Response) -> Any:
        if respuesta.status_code == 204 or not respuesta.content:
            return None

        try:
            return respuesta.json()
        except ValueError:
            return respuesta.text
```

- [ ] **Step 8: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/shared/infrastructure/gcp/cloud_run/test_client.py -v`
Expected: PASS (2 tests)

- [ ] **Step 9: Commit**

```bash
git add shared/infrastructure/gcp/cloud_run/token_provider.py shared/infrastructure/gcp/cloud_run/client.py tests/unit/shared/infrastructure/gcp/cloud_run/test_token_provider.py tests/unit/shared/infrastructure/gcp/cloud_run/test_client.py
git commit -m "feat: proveedor de token y cliente saliente Cloud Run"
```

---

## Task 8: Contratos de autenticación entrante + verificador de token + dependencia FastAPI

**Files:**
- Create: `shared/application/client_auth/dto.py`
- Create: `shared/application/client_auth/errors.py`
- Create: `shared/application/client_auth/ports.py`
- Create: `shared/infrastructure/gcp/authentication/token_verifier.py`
- Create: `shared/infrastructure/api/dependencies/authentication.py`
- Test: `tests/unit/shared/infrastructure/gcp/authentication/test_token_verifier.py`
- Test: `tests/unit/shared/infrastructure/api/dependencies/test_authentication.py`

**Interfaces:**
- Produces: `IdentidadAutenticada(email: str, claims: dict = {})` (dataclass).
- Produces: `TokenInvalidoError(Exception)`, `EmailTokenNoDisponibleError(Exception)`.
- Produces: `VerificadorTokenIdentidadPort.verificar(token: str) -> IdentidadAutenticada` (ABC).
- Produces: `VerificadorTokenIdentidadGoogle(audiencia: str)` implementando el port anterior.
- Produces: `shared.infrastructure.api.dependencies.authentication.autenticar_cliente(authorization: str | None = Header()) -> IdentidadAutenticada` — dependencia FastAPI que valida el header `Authorization: Bearer <token>` y lanza `HTTPException(401)` si falta o es inválido. Disponible para que cualquier módulo la use en rutas que necesiten aceptar llamadas autenticadas de otro servicio Cloud Run (el módulo de ejemplo `tareas` no la usa, para no requerir credenciales GCP reales en desarrollo local).

- [ ] **Step 1: Escribir el test del verificador de token**

```python
# tests/unit/shared/infrastructure/gcp/authentication/test_token_verifier.py
from unittest.mock import patch

import pytest

from shared.application.client_auth.errors import (
    EmailTokenNoDisponibleError,
    TokenInvalidoError,
)
from shared.infrastructure.gcp.authentication.token_verifier import (
    VerificadorTokenIdentidadGoogle,
)


@patch("shared.infrastructure.gcp.authentication.token_verifier.id_token.verify_oauth2_token")
def test_verificar_retorna_identidad_autenticada(verify_mock):
    verify_mock.return_value = {"email": "servicio@proyecto.iam.gserviceaccount.com"}

    verificador = VerificadorTokenIdentidadGoogle("https://mi-servicio.example.com")
    identidad = verificador.verificar("token-valido")

    assert identidad.email == "servicio@proyecto.iam.gserviceaccount.com"


@patch("shared.infrastructure.gcp.authentication.token_verifier.id_token.verify_oauth2_token")
def test_verificar_lanza_token_invalido_si_falla_la_verificacion(verify_mock):
    verify_mock.side_effect = ValueError("token expirado")

    verificador = VerificadorTokenIdentidadGoogle("https://mi-servicio.example.com")

    with pytest.raises(TokenInvalidoError):
        verificador.verificar("token-expirado")


@patch("shared.infrastructure.gcp.authentication.token_verifier.id_token.verify_oauth2_token")
def test_verificar_lanza_error_si_no_hay_email_en_el_token(verify_mock):
    verify_mock.return_value = {"sub": "12345"}

    verificador = VerificadorTokenIdentidadGoogle("https://mi-servicio.example.com")

    with pytest.raises(EmailTokenNoDisponibleError):
        verificador.verificar("token-sin-email")
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/shared/infrastructure/gcp/authentication/test_token_verifier.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 3: Crear `shared/application/client_auth/dto.py`**

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class IdentidadAutenticada:
    email: str
    claims: dict[str, Any] = field(default_factory=dict)
```

- [ ] **Step 4: Crear `shared/application/client_auth/errors.py`**

```python
class TokenInvalidoError(Exception):
    def __init__(self, detalle: str):
        super().__init__(f"Token invalido: {detalle}")
        self.detalle = detalle


class EmailTokenNoDisponibleError(Exception):
    def __init__(self):
        super().__init__("El token no incluye un email valido.")
```

- [ ] **Step 5: Crear `shared/application/client_auth/ports.py`**

```python
from abc import ABC, abstractmethod

from shared.application.client_auth.dto import IdentidadAutenticada


class VerificadorTokenIdentidadPort(ABC):
    @abstractmethod
    def verificar(self, token: str) -> IdentidadAutenticada: ...
```

- [ ] **Step 6: Crear `shared/infrastructure/gcp/authentication/token_verifier.py`**

```python
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from shared.application.client_auth.dto import IdentidadAutenticada
from shared.application.client_auth.errors import (
    EmailTokenNoDisponibleError,
    TokenInvalidoError,
)
from shared.application.client_auth.ports import VerificadorTokenIdentidadPort


class VerificadorTokenIdentidadGoogle(VerificadorTokenIdentidadPort):
    """Verifica tokens de identidad emitidos por Google."""

    def __init__(self, audiencia: str):
        self._audiencia = audiencia
        self._request_adapter = google_requests.Request()

    def verificar(self, token: str) -> IdentidadAutenticada:
        try:
            info = id_token.verify_oauth2_token(
                token,
                self._request_adapter,
                self._audiencia,
            )
        except Exception as exc:
            raise TokenInvalidoError(detalle=str(exc)) from exc

        email = info.get("email")
        if not isinstance(email, str) or not email.strip():
            raise EmailTokenNoDisponibleError()

        return IdentidadAutenticada(email=email.strip(), claims=dict(info))
```

- [ ] **Step 7: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/shared/infrastructure/gcp/authentication/test_token_verifier.py -v`
Expected: PASS (3 tests)

- [ ] **Step 8: Escribir el test de la dependencia FastAPI**

```python
# tests/unit/shared/infrastructure/api/dependencies/test_authentication.py
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from shared.application.client_auth.dto import IdentidadAutenticada
from shared.application.client_auth.errors import TokenInvalidoError
from shared.infrastructure.api.dependencies.authentication import autenticar_cliente


def test_autenticar_cliente_lanza_401_si_no_hay_header():
    with pytest.raises(HTTPException) as exc_info:
        autenticar_cliente(authorization=None)

    assert exc_info.value.status_code == 401


@patch("shared.infrastructure.api.dependencies.authentication._obtener_verificador")
def test_autenticar_cliente_retorna_identidad_si_el_token_es_valido(obtener_verificador_mock):
    verificador_falso = MagicMock()
    verificador_falso.verificar.return_value = IdentidadAutenticada(email="x@y.com")
    obtener_verificador_mock.return_value = verificador_falso

    identidad = autenticar_cliente(authorization="Bearer token-valido")

    assert identidad.email == "x@y.com"
    verificador_falso.verificar.assert_called_once_with("token-valido")


@patch("shared.infrastructure.api.dependencies.authentication._obtener_verificador")
def test_autenticar_cliente_lanza_401_si_el_token_es_invalido(obtener_verificador_mock):
    verificador_falso = MagicMock()
    verificador_falso.verificar.side_effect = TokenInvalidoError("expirado")
    obtener_verificador_mock.return_value = verificador_falso

    with pytest.raises(HTTPException) as exc_info:
        autenticar_cliente(authorization="Bearer token-invalido")

    assert exc_info.value.status_code == 401
```

- [ ] **Step 9: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/shared/infrastructure/api/dependencies/test_authentication.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'shared.infrastructure.api.dependencies.authentication'`

- [ ] **Step 10: Crear `shared/infrastructure/api/dependencies/authentication.py`**

```python
from typing import Annotated

from fastapi import Header, HTTPException

from config.settings import settings
from shared.application.client_auth.dto import IdentidadAutenticada
from shared.application.client_auth.errors import (
    EmailTokenNoDisponibleError,
    TokenInvalidoError,
)
from shared.infrastructure.gcp.authentication.token_verifier import (
    VerificadorTokenIdentidadGoogle,
)

_verificador: VerificadorTokenIdentidadGoogle | None = None


def _obtener_verificador() -> VerificadorTokenIdentidadGoogle:
    global _verificador
    if _verificador is None:
        if not settings.GOOGLE_CLOUD_RUN_AUDIENCE:
            raise RuntimeError(
                "GOOGLE_CLOUD_RUN_AUDIENCE debe estar configurado para autenticar clientes."
            )
        _verificador = VerificadorTokenIdentidadGoogle(settings.GOOGLE_CLOUD_RUN_AUDIENCE)
    return _verificador


def autenticar_cliente(
    authorization: Annotated[str | None, Header()] = None,
) -> IdentidadAutenticada:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token de autenticacion requerido.")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        return _obtener_verificador().verificar(token)
    except (TokenInvalidoError, EmailTokenNoDisponibleError) as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
```

- [ ] **Step 11: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/shared/infrastructure/api/dependencies/test_authentication.py -v`
Expected: PASS (3 tests)

- [ ] **Step 12: Commit**

```bash
git add shared/application/client_auth/ shared/infrastructure/gcp/authentication/ shared/infrastructure/api/dependencies/authentication.py tests/unit/shared/infrastructure/gcp/authentication/ tests/unit/shared/infrastructure/api/dependencies/
git commit -m "feat: verificacion de tokens entrantes Cloud Run y dependencia FastAPI"
```

---

## Task 9: Bootstrap de la aplicación compartida (`create_app`)

**Files:**
- Create: `shared/bootstrap/application.py`
- Test: `tests/unit/shared/bootstrap/test_application.py`

**Interfaces:**
- Consumes: `config.logger.configurar_logging` (Task 1), `shared.infrastructure.api.error_handlers.register_error_handlers` (Task 3), `shared.infrastructure.persistence.mongo.database.mongo_manager` (Task 5).
- Produces: `shared.bootstrap.application.create_app() -> FastAPI`. En esta tarea no registra módulos de negocio todavía (se agrega en Task 13).

- [ ] **Step 1: Escribir el test usando `TestClient`, mockeando la conexión a Mongo**

```python
# tests/unit/shared/bootstrap/test_application.py
from unittest.mock import patch

from fastapi.testclient import TestClient


def test_create_app_expone_endpoint_raiz_con_cabeceras_de_seguridad():
    with (
        patch("shared.infrastructure.persistence.mongo.database.mongo_manager.connect"),
        patch("shared.infrastructure.persistence.mongo.database.mongo_manager.close"),
    ):
        from shared.bootstrap.application import create_app

        with TestClient(create_app()) as cliente:
            respuesta = cliente.get("/")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/shared/bootstrap/test_application.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'shared.bootstrap.application'`

- [ ] **Step 3: Crear `shared/bootstrap/application.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from config.logger import configurar_logging
from shared.infrastructure.api.error_handlers import register_error_handlers
from shared.infrastructure.persistence.mongo.database import mongo_manager

configurar_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    mongo_manager.connect()
    try:
        yield
    finally:
        mongo_manager.close()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response


def create_app() -> FastAPI:
    app = FastAPI(docs_url="/docs", redoc_url=None, lifespan=lifespan)
    register_error_handlers(app)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def raiz():
        return {"status": "ok"}

    return app
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/shared/bootstrap/test_application.py -v`
Expected: PASS (1 test)

- [ ] **Step 5: Commit**

```bash
git add shared/bootstrap/application.py tests/unit/shared/bootstrap/test_application.py
git commit -m "feat: bootstrap de la aplicacion FastAPI compartida"
```

---

## Task 10: Módulo `tareas` — domain

**Files:**
- Create: `modules/tareas/domain/entities.py`
- Create: `modules/tareas/domain/errors.py`
- Test: `tests/unit/modules/tareas/domain/test_entities.py`
- Test: `tests/unit/modules/tareas/domain/test_errors.py`

**Interfaces:**
- Consumes: `shared.domain.errors.DomainError` (Task 2).
- Produces: `Tarea(id: str | None, titulo: str, completada: bool, fecha_creacion: datetime)` (dataclass frozen).
- Produces: `TituloTareaVacioError(DomainError)` con `status_code = 422`.

- [ ] **Step 1: Escribir los tests de dominio (puros, sin mocks)**

```python
# tests/unit/modules/tareas/domain/test_entities.py
import dataclasses
from datetime import UTC, datetime

import pytest

from modules.tareas.domain.entities import Tarea


def test_tarea_se_crea_con_los_campos_esperados():
    tarea = Tarea(
        id="1",
        titulo="Escribir el plan",
        completada=False,
        fecha_creacion=datetime(2026, 7, 23, tzinfo=UTC),
    )

    assert tarea.id == "1"
    assert tarea.titulo == "Escribir el plan"
    assert tarea.completada is False


def test_tarea_es_inmutable():
    tarea = Tarea(
        id="1",
        titulo="Escribir el plan",
        completada=False,
        fecha_creacion=datetime(2026, 7, 23, tzinfo=UTC),
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        tarea.titulo = "otro titulo"
```

```python
# tests/unit/modules/tareas/domain/test_errors.py
from modules.tareas.domain.errors import TituloTareaVacioError


def test_titulo_tarea_vacio_error_tiene_status_code_422():
    error = TituloTareaVacioError()

    assert error.status_code == 422
    assert "titulo" in error.mensaje.lower()
```

- [ ] **Step 2: Ejecutar y confirmar que fallan**

Run: `pytest tests/unit/modules/tareas/domain/ -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'modules.tareas.domain.entities'`

- [ ] **Step 3: Crear `modules/tareas/domain/entities.py`**

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class Tarea:
    id: str | None
    titulo: str
    completada: bool
    fecha_creacion: datetime
```

- [ ] **Step 4: Crear `modules/tareas/domain/errors.py`**

```python
from shared.domain.errors import DomainError


class TituloTareaVacioError(DomainError):
    status_code = 422

    def __init__(self):
        super().__init__("El titulo de la tarea no puede estar vacio.")
```

- [ ] **Step 5: Ejecutar y confirmar que pasan**

Run: `pytest tests/unit/modules/tareas/domain/ -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add modules/tareas/domain/ tests/unit/modules/tareas/domain/
git commit -m "feat: dominio del modulo de ejemplo tareas"
```

---

## Task 11: Módulo `tareas` — application

**Files:**
- Create: `modules/tareas/application/dto/crear_tarea_dto.py`
- Create: `modules/tareas/application/dto/tarea_dto.py`
- Create: `modules/tareas/application/ports/tarea_repository.py`
- Create: `modules/tareas/application/services/crear_tarea.py`
- Create: `modules/tareas/application/services/listar_tareas.py`
- Test: `tests/unit/modules/tareas/application/services/test_crear_tarea.py`
- Test: `tests/unit/modules/tareas/application/services/test_listar_tareas.py`

**Interfaces:**
- Consumes: `Tarea`, `TituloTareaVacioError` (Task 10).
- Produces: `CrearTareaDTO(titulo: str)`, `TareaDTO(id, titulo, completada, fecha_creacion)`.
- Produces: `TareaRepositoryPort` (ABC) con `guardar(tarea: Tarea) -> Tarea` y `listar() -> list[Tarea]`.
- Produces: `CrearTareaService(tarea_repository: TareaRepositoryPort).ejecutar(dto: CrearTareaDTO) -> TareaDTO`.
- Produces: `ListarTareasService(tarea_repository: TareaRepositoryPort).ejecutar() -> list[TareaDTO]`. Ambos servicios son consumidos por Task 12 (`infrastructure/api/dependencies.py`).

- [ ] **Step 1: Escribir el test de `CrearTareaService` con el repositorio mockeado**

```python
# tests/unit/modules/tareas/application/services/test_crear_tarea.py
from unittest.mock import AsyncMock

import pytest

from modules.tareas.application.dto.crear_tarea_dto import CrearTareaDTO
from modules.tareas.application.services.crear_tarea import CrearTareaService
from modules.tareas.domain.entities import Tarea
from modules.tareas.domain.errors import TituloTareaVacioError


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.guardar.side_effect = lambda tarea: Tarea(
        id="1",
        titulo=tarea.titulo,
        completada=tarea.completada,
        fecha_creacion=tarea.fecha_creacion,
    )
    return mock


async def test_crear_tarea_guarda_la_entidad_con_titulo_recortado(repositorio_mock):
    service = CrearTareaService(repositorio_mock)

    resultado = await service.ejecutar(CrearTareaDTO(titulo="  Escribir el plan  "))

    assert resultado.id == "1"
    assert resultado.titulo == "Escribir el plan"
    assert resultado.completada is False
    repositorio_mock.guardar.assert_called_once()
    tarea_guardada = repositorio_mock.guardar.call_args.args[0]
    assert tarea_guardada.titulo == "Escribir el plan"


async def test_crear_tarea_lanza_error_si_el_titulo_esta_vacio(repositorio_mock):
    service = CrearTareaService(repositorio_mock)

    with pytest.raises(TituloTareaVacioError):
        await service.ejecutar(CrearTareaDTO(titulo="   "))

    repositorio_mock.guardar.assert_not_called()
```

```python
# tests/unit/modules/tareas/application/services/test_listar_tareas.py
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.tareas.application.services.listar_tareas import ListarTareasService
from modules.tareas.domain.entities import Tarea


async def test_listar_tareas_mapea_entidades_a_dto():
    repositorio_mock = AsyncMock()
    repositorio_mock.listar.return_value = [
        Tarea(id="1", titulo="A", completada=False, fecha_creacion=datetime(2026, 7, 23, tzinfo=UTC)),
        Tarea(id="2", titulo="B", completada=True, fecha_creacion=datetime(2026, 7, 22, tzinfo=UTC)),
    ]
    service = ListarTareasService(repositorio_mock)

    resultado = await service.ejecutar()

    assert [tarea_dto.id for tarea_dto in resultado] == ["1", "2"]
    assert resultado[1].completada is True
```

- [ ] **Step 2: Ejecutar y confirmar que fallan**

Run: `pytest tests/unit/modules/tareas/application/ -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'modules.tareas.application.dto.crear_tarea_dto'`

- [ ] **Step 3: Crear `modules/tareas/application/dto/crear_tarea_dto.py`**

```python
from dataclasses import dataclass


@dataclass
class CrearTareaDTO:
    titulo: str
```

- [ ] **Step 4: Crear `modules/tareas/application/dto/tarea_dto.py`**

```python
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TareaDTO:
    id: str
    titulo: str
    completada: bool
    fecha_creacion: datetime
```

- [ ] **Step 5: Crear `modules/tareas/application/ports/tarea_repository.py`**

```python
from abc import ABC, abstractmethod

from modules.tareas.domain.entities import Tarea


class TareaRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, tarea: Tarea) -> Tarea: ...

    @abstractmethod
    async def listar(self) -> list[Tarea]: ...
```

- [ ] **Step 6: Crear `modules/tareas/application/services/crear_tarea.py`**

```python
from datetime import UTC, datetime

from modules.tareas.application.dto.crear_tarea_dto import CrearTareaDTO
from modules.tareas.application.dto.tarea_dto import TareaDTO
from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.tareas.domain.entities import Tarea
from modules.tareas.domain.errors import TituloTareaVacioError


class CrearTareaService:
    def __init__(self, tarea_repository: TareaRepositoryPort):
        self._tarea_repository = tarea_repository

    async def ejecutar(self, dto: CrearTareaDTO) -> TareaDTO:
        titulo = dto.titulo.strip()
        if not titulo:
            raise TituloTareaVacioError()

        tarea = Tarea(
            id=None,
            titulo=titulo,
            completada=False,
            fecha_creacion=datetime.now(UTC),
        )
        tarea_guardada = await self._tarea_repository.guardar(tarea)

        return TareaDTO(
            id=tarea_guardada.id,
            titulo=tarea_guardada.titulo,
            completada=tarea_guardada.completada,
            fecha_creacion=tarea_guardada.fecha_creacion,
        )
```

- [ ] **Step 7: Crear `modules/tareas/application/services/listar_tareas.py`**

```python
from modules.tareas.application.dto.tarea_dto import TareaDTO
from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort


class ListarTareasService:
    def __init__(self, tarea_repository: TareaRepositoryPort):
        self._tarea_repository = tarea_repository

    async def ejecutar(self) -> list[TareaDTO]:
        tareas = await self._tarea_repository.listar()
        return [
            TareaDTO(
                id=tarea.id,
                titulo=tarea.titulo,
                completada=tarea.completada,
                fecha_creacion=tarea.fecha_creacion,
            )
            for tarea in tareas
        ]
```

- [ ] **Step 8: Ejecutar y confirmar que pasan**

Run: `pytest tests/unit/modules/tareas/application/ -v`
Expected: PASS (3 tests)

- [ ] **Step 9: Commit**

```bash
git add modules/tareas/application/ tests/unit/modules/tareas/application/
git commit -m "feat: capa application del modulo de ejemplo tareas"
```

---

## Task 12: Módulo `tareas` — infrastructure + bootstrap del módulo

**Files:**
- Create: `modules/tareas/infrastructure/api/schemas.py`
- Create: `modules/tareas/infrastructure/api/routes.py`
- Create: `modules/tareas/infrastructure/api/dependencies.py`
- Create: `modules/tareas/infrastructure/persistence/mongo/tarea_repository.py`
- Create: `modules/tareas/bootstrap.py`
- Test: `tests/unit/modules/tareas/infrastructure/persistence/mongo/test_tarea_repository.py`
- Test: `tests/unit/modules/tareas/infrastructure/api/test_routes.py`

**Interfaces:**
- Consumes: `CrearTareaService`, `ListarTareasService`, `TareaRepositoryPort`, `Tarea` (Tasks 10-11), `mongo_manager` (Task 5).
- Produces: `CrearTareaRequest`, `TareaResponse` (Pydantic).
- Produces: `MongoTareaRepository()` implementando `TareaRepositoryPort`, con funciones de mapeo privadas `_doc_a_entidad`/`_entidad_a_doc`.
- Produces: `router` (`APIRouter(prefix="/api/tareas", tags=["tareas"])`) con `POST /api/tareas` y `GET /api/tareas`.
- Produces: `modules.tareas.bootstrap.register_module(app: FastAPI) -> None` — consumido por Task 13.

- [ ] **Step 1: Escribir el test de las funciones de mapeo Mongo (puras, sin conexión real)**

```python
# tests/unit/modules/tareas/infrastructure/persistence/mongo/test_tarea_repository.py
from datetime import UTC, datetime

from bson import ObjectId

from modules.tareas.domain.entities import Tarea
from modules.tareas.infrastructure.persistence.mongo.tarea_repository import (
    _doc_a_entidad,
    _entidad_a_doc,
)


def test_entidad_a_doc_no_incluye_el_id():
    tarea = Tarea(
        id=None,
        titulo="Escribir el plan",
        completada=False,
        fecha_creacion=datetime(2026, 7, 23, tzinfo=UTC),
    )

    doc = _entidad_a_doc(tarea)

    assert "id" not in doc
    assert "_id" not in doc
    assert doc["titulo"] == "Escribir el plan"


def test_doc_a_entidad_convierte_object_id_a_string():
    object_id = ObjectId()
    doc = {
        "_id": object_id,
        "titulo": "Escribir el plan",
        "completada": False,
        "fecha_creacion": datetime(2026, 7, 23, tzinfo=UTC),
    }

    tarea = _doc_a_entidad(doc)

    assert tarea.id == str(object_id)
    assert tarea.titulo == "Escribir el plan"
```

- [ ] **Step 2: Ejecutar y confirmar que falla**

Run: `pytest tests/unit/modules/tareas/infrastructure/persistence/mongo/test_tarea_repository.py -v`
Expected: FAIL con `ModuleNotFoundError`

- [ ] **Step 3: Crear `modules/tareas/infrastructure/persistence/mongo/tarea_repository.py`**

```python
from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.tareas.domain.entities import Tarea
from shared.infrastructure.persistence.mongo.database import mongo_manager


def _entidad_a_doc(tarea: Tarea) -> dict:
    return {
        "titulo": tarea.titulo,
        "completada": tarea.completada,
        "fecha_creacion": tarea.fecha_creacion,
    }


def _doc_a_entidad(doc: dict) -> Tarea:
    return Tarea(
        id=str(doc["_id"]),
        titulo=doc["titulo"],
        completada=doc["completada"],
        fecha_creacion=doc["fecha_creacion"],
    )


class MongoTareaRepository(TareaRepositoryPort):
    def __init__(self, collection_name: str = "tareas"):
        self._collection_name = collection_name

    @property
    def _collection(self):
        return mongo_manager.get_database()[self._collection_name]

    async def guardar(self, tarea: Tarea) -> Tarea:
        resultado = await self._collection.insert_one(_entidad_a_doc(tarea))
        documento = await self._collection.find_one({"_id": resultado.inserted_id})
        return _doc_a_entidad(documento)

    async def listar(self) -> list[Tarea]:
        documentos = (
            await self._collection.find({})
            .sort("fecha_creacion", -1)
            .to_list(length=None)
        )
        return [_doc_a_entidad(documento) for documento in documentos]
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/modules/tareas/infrastructure/persistence/mongo/test_tarea_repository.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Crear `modules/tareas/infrastructure/api/schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel, Field


class CrearTareaRequest(BaseModel):
    titulo: str = Field(min_length=1)


class TareaResponse(BaseModel):
    id: str
    titulo: str
    completada: bool
    fecha_creacion: datetime
```

- [ ] **Step 6: Crear `modules/tareas/infrastructure/api/dependencies.py`**

```python
from functools import lru_cache

from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.tareas.application.services.crear_tarea import CrearTareaService
from modules.tareas.application.services.listar_tareas import ListarTareasService
from modules.tareas.infrastructure.persistence.mongo.tarea_repository import (
    MongoTareaRepository,
)


@lru_cache(maxsize=1)
def get_tarea_repository() -> TareaRepositoryPort:
    return MongoTareaRepository()


def get_crear_tarea_service() -> CrearTareaService:
    return CrearTareaService(tarea_repository=get_tarea_repository())


def get_listar_tareas_service() -> ListarTareasService:
    return ListarTareasService(tarea_repository=get_tarea_repository())
```

- [ ] **Step 7: Crear `modules/tareas/infrastructure/api/routes.py`**

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
) -> TareaResponse:
    tarea = await service.ejecutar(CrearTareaDTO(titulo=body.titulo))
    return TareaResponse(**tarea.__dict__)


@router.get(
    "",
    summary="Lista las tareas existentes",
)
async def listar_tareas(
    service: Annotated[ListarTareasService, Depends(get_listar_tareas_service)],
) -> list[TareaResponse]:
    tareas = await service.ejecutar()
    return [TareaResponse(**tarea.__dict__) for tarea in tareas]
```

- [ ] **Step 8: Crear `modules/tareas/bootstrap.py`**

```python
from fastapi import FastAPI

from modules.tareas.infrastructure.api.routes import router


def register_module(app: FastAPI) -> None:
    app.include_router(router)
```

- [ ] **Step 9: Escribir el test de las rutas usando `TestClient` con un repositorio en memoria (sin Mongo real)**

```python
# tests/unit/modules/tareas/infrastructure/api/test_routes.py
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
    assert respuesta_crear.json()["titulo"] == "Escribir el plan"

    respuesta_listar = cliente.get("/api/tareas")
    assert respuesta_listar.status_code == 200
    assert len(respuesta_listar.json()) == 1


def test_crear_tarea_con_titulo_vacio_retorna_422():
    cliente = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/tareas", json={"titulo": "   "})

    assert respuesta.status_code == 422
```

- [ ] **Step 10: Ejecutar el test de rutas y confirmar que pasa**

`routes.py`/`dependencies.py`/`bootstrap.py` ya se crearon en los Steps 5-8, así que este test verifica el wiring completo de la capa infra en lugar de seguir red-green estricto.

Run: `pytest tests/unit/modules/tareas/infrastructure/api/test_routes.py -v`
Expected: PASS (2 tests)

- [ ] **Step 11: Ejecutar toda la suite del módulo y confirmar que pasa**

Run: `pytest tests/unit/modules/tareas/ -v`
Expected: PASS (todas las pruebas del módulo `tareas`)

- [ ] **Step 12: Commit**

```bash
git add modules/tareas/infrastructure/ modules/tareas/bootstrap.py tests/unit/modules/tareas/infrastructure/
git commit -m "feat: capa infrastructure y bootstrap del modulo de ejemplo tareas"
```

---

## Task 13: Wiring final — registrar `tareas` en el bootstrap compartido + `main.py`

**Files:**
- Modify: `shared/bootstrap/application.py`
- Create: `main.py`
- Test: `tests/unit/shared/bootstrap/test_application.py` (agregar caso end-to-end)

**Interfaces:**
- Consumes: `modules.tareas.bootstrap.register_module` (Task 12), `shared.bootstrap.application.create_app` (Task 9).
- Produces: `main.app` — instancia FastAPI lista para `uvicorn`/`gunicorn`.

- [ ] **Step 1: Agregar el test end-to-end en `tests/unit/shared/bootstrap/test_application.py`**

```python
# agregar al final de tests/unit/shared/bootstrap/test_application.py
from modules.tareas.application.ports.tarea_repository import TareaRepositoryPort
from modules.tareas.domain.entities import Tarea
from modules.tareas.infrastructure.api.dependencies import (
    get_crear_tarea_service,
    get_listar_tareas_service,
)
from modules.tareas.application.services.crear_tarea import CrearTareaService
from modules.tareas.application.services.listar_tareas import ListarTareasService


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


def test_create_app_registra_el_modulo_tareas():
    with (
        patch("shared.infrastructure.persistence.mongo.database.mongo_manager.connect"),
        patch("shared.infrastructure.persistence.mongo.database.mongo_manager.close"),
    ):
        from shared.bootstrap.application import create_app

        app = create_app()
        repositorio = _RepositorioEnMemoria()
        app.dependency_overrides[get_crear_tarea_service] = lambda: CrearTareaService(repositorio)
        app.dependency_overrides[get_listar_tareas_service] = lambda: ListarTareasService(repositorio)

        with TestClient(app) as cliente:
            respuesta_crear = cliente.post("/api/tareas", json={"titulo": "Probar wiring"})
            respuesta_listar = cliente.get("/api/tareas")

    assert respuesta_crear.status_code == 201
    assert respuesta_listar.status_code == 200
    assert len(respuesta_listar.json()) == 1
```

- [ ] **Step 2: Ejecutar y confirmar que falla (404 en `/api/tareas`, el módulo aún no está registrado)**

Run: `pytest tests/unit/shared/bootstrap/test_application.py -v`
Expected: FAIL — `respuesta_crear.status_code == 404`

- [ ] **Step 3: Modificar `shared/bootstrap/application.py` para registrar el módulo**

Agregar el import junto a los demás imports:
```python
from modules.tareas.bootstrap import register_module as register_module_tareas
```

Agregar la llamada dentro de `create_app()`, justo después de `register_error_handlers(app)`:
```python
    register_error_handlers(app)
    register_module_tareas(app)
```

- [ ] **Step 4: Ejecutar y confirmar que pasa**

Run: `pytest tests/unit/shared/bootstrap/test_application.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Crear `main.py`**

```python
import uvicorn

from shared.bootstrap.application import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="debug",
    )
```

- [ ] **Step 6: Ejecutar toda la suite de tests del repo y confirmar que pasa completa**

Run: `pytest -v`
Expected: PASS (todos los tests de Tasks 1-13)

- [ ] **Step 7: Commit**

```bash
git add shared/bootstrap/application.py main.py tests/unit/shared/bootstrap/test_application.py
git commit -m "feat: registrar modulo tareas y agregar entry point main.py"
```

---

## Task 14: Entorno de desarrollo local — `docker-compose.yml`, `Dockerfile`, `README.md`

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `README.md`

**Interfaces:**
- Ninguna interfaz de código — este task es infraestructura de desarrollo/despliegue local. Verificación manual (no pytest).

- [ ] **Step 1: Crear `Dockerfile` (igual al de `ms-continuum`, orden de capas ya correcto)**

```dockerfile
# Imagen base de Python 3.12.8. Considera 'python:3.12.8-slim-bookworm' para menor tamaño.
FROM python:3.12.8-slim-bookworm

# Directorio de trabajo en el contenedor.
WORKDIR /app

# Deshabilita el cache de pip para builds mas limpios y rapidos.
ENV PIP_NO_CACHE_DIR=1

# Copia el archivo de requerimientos e instala las dependencias.
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Asegura que los binarios de pip esten en el PATH del sistema.
# Esto es crucial para que comandos como 'gunicorn' sean encontrados.
ENV PATH="/usr/local/bin:${PATH}"

# Copia el resto de tu aplicacion al directorio de trabajo.
COPY . .
ENV PORT=8080
# Comando para iniciar la aplicacion Gunicorn con worker de Uvicorn.
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "main:app", "--bind", "0.0.0.0:8080"]
```

- [ ] **Step 2: Crear `docker-compose.yml`**

```yaml
services:
  mongo:
    image: mongo:7
    container_name: fastapi-cloud-run-mongo-local
    ports:
      - "27017:27017"
    volumes:
      - mongo_local_data:/data/db

volumes:
  mongo_local_data:
```

- [ ] **Step 3: Crear `README.md`**

```markdown
# fastapi-cloud-run — Plantilla base para microservicios en Cloud Run

Plantilla de referencia para iniciar microservicios FastAPI desplegados en
Cloud Run, con arquitectura hexagonal (`domain → application → infrastructure`).
Incluye un modulo de ejemplo (`tareas`) funcional de punta a punta.

## Requisitos

- Python 3.12
- Docker (para MongoDB local y para construir la imagen)

## Desarrollo local

```bash
# 1. Levantar MongoDB local
docker compose up -d mongo

# 2. Crear entorno virtual e instalar dependencias
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements-dev.txt

# 3. Configurar variables de entorno
copy .env.example .env      # Windows (cp en Linux/Mac)
# .env ya viene con ENTORNO=local y MONGO_URL apuntando al contenedor local

# 4. Arrancar la aplicacion
python main.py
```

Endpoints disponibles en `http://localhost:8080/docs`.

## Tests

```bash
pytest
```

## Construir y probar la imagen Docker localmente

```bash
docker build -t fastapi-cloud-run-template .
docker run --rm -p 8080:8080 --env-file .env fastapi-cloud-run-template
```

Nota: para correr contra Mongo local desde el contenedor, cambia
`MONGO_URL` en `.env` a `mongodb://host.docker.internal:27017`.

## Despliegue

El despliegue a Cloud Run se hace vía el trigger de Cloud Build ya configurado
con "Continuous Deployment" nativo de Cloud Run, usando el `cloudbuild.yaml`
versionado en este repo (ver seccion correspondiente). Este pipeline corre los
tests como gate y reutiliza el cache de capas Docker para que un cambio de
solo codigo no reinstale las dependencias desde cero.

## Estructura del proyecto

Ver `.claude/ARCHITECTURE.md` para el detalle de capas y convenciones, y
`.claude/TEMPLATE.md` para el checklist de como agregar un modulo nuevo
(usando `modules/tareas/` como referencia).

## Como agregar un modulo nuevo

Seguir `.claude/WORKFLOW.md` (flujo de 4 fases) y `.claude/TEMPLATE.md`
(checklist de construccion), usando `modules/tareas/` como plantilla a
copiar y renombrar.
```

- [ ] **Step 4: Verificación manual — levantar Mongo local y correr la app**

Run: `docker compose up -d mongo`
Expected: contenedor `fastapi-cloud-run-mongo-local` corriendo (`docker ps` lo muestra)

Run: `copy .env.example .env` (Windows) y luego `python main.py`
Expected: la app arranca en `http://localhost:8080`, `GET /` responde `{"status": "ok"}`, `POST /api/tareas` con `{"titulo": "prueba"}` responde 201 y la tarea aparece en `GET /api/tareas`

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker-compose.yml README.md
git commit -m "feat: entorno de desarrollo local con docker-compose y README"
```

---

## Task 15: CI/CD — `cloudbuild.yaml` con cache de capas y gate de tests

**Files:**
- Create: `cloudbuild.yaml`

**Interfaces:**
- Ninguna interfaz de código Python. Verificación: validez del YAML.

- [ ] **Step 1: Crear `cloudbuild.yaml`**

```yaml
substitutions:
  _SERVICE_NAME: fastapi-cloud-run-template
  _REGION: us-central1
  _REPOSITORY: microservicios

steps:
  - id: test
    name: python:3.12.8-slim-bookworm
    entrypoint: bash
    args:
      - -c
      - |
        pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt
        pytest tests/unit -v

  - id: pull-cache
    name: gcr.io/cloud-builders/docker
    entrypoint: bash
    args:
      - -c
      - |
        docker pull "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE_NAME}:latest" || true

  - id: build
    name: gcr.io/cloud-builders/docker
    args:
      - build
      - "--cache-from"
      - "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE_NAME}:latest"
      - "-t"
      - "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE_NAME}:$SHORT_SHA"
      - "-t"
      - "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE_NAME}:latest"
      - .

  - id: push-sha
    name: gcr.io/cloud-builders/docker
    args: ["push", "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE_NAME}:$SHORT_SHA"]

  - id: push-latest
    name: gcr.io/cloud-builders/docker
    args: ["push", "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE_NAME}:latest"]

  - id: deploy
    name: gcr.io/google-cloud-sdk/slim
    entrypoint: gcloud
    args:
      - run
      - deploy
      - "${_SERVICE_NAME}"
      - "--image=${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE_NAME}:$SHORT_SHA"
      - "--region=${_REGION}"
      - "--platform=managed"

images:
  - "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE_NAME}:$SHORT_SHA"
  - "${_REGION}-docker.pkg.dev/$PROJECT_ID/${_REPOSITORY}/${_SERVICE_NAME}:latest"

options:
  logging: CLOUD_LOGGING_ONLY
```

- [ ] **Step 2: Validar que el YAML es sintácticamente correcto**

Run: `python -c "import yaml; yaml.safe_load(open('cloudbuild.yaml', encoding='utf-8')); print('OK')"`
Expected: `OK` (sin excepciones)

- [ ] **Step 3: Commit**

```bash
git add cloudbuild.yaml
git commit -m "feat: cloudbuild.yaml con cache de capas y tests como gate de despliegue"
```

*Nota operativa (no es un step de código): para que este archivo tome efecto, hay que editar el trigger de Cloud Build que la función "Continuous Deployment" de Cloud Run ya creó, apuntándolo a `cloudbuild.yaml` en lugar de la configuración inferida por defecto. Esto se hace una vez por proyecto real derivado de esta plantilla, en la consola de Cloud Build o con `gcloud builds triggers update`.*

---

## Task 16: Documentación `.claude/*.md` + `CLAUDE.md` raíz

**Files:**
- Create: `CLAUDE.md`
- Create: `.claude/ARCHITECTURE.md`
- Create: `.claude/CONVENTIONS.md`
- Create: `.claude/STACK.md`
- Create: `.claude/TEMPLATE.md`
- Create: `.claude/TESTING.md`
- Create: `.claude/WORKFLOW.md`
- Create: `.claude/SOLID_CHECKLIST.md`
- Create: `.claude/API.md`
- Create: `.claude/MONGODB.md`
- Create: `.claude/MONGODB_MODELING.md`
- Create: `.claude/MONGODB_QUERIES.md`

**Interfaces:**
- Ninguna interfaz de código. Verificación: cada archivo referenciado en la tabla de `CLAUDE.md` existe.

- [ ] **Step 1: Crear `.claude/ARCHITECTURE.md`** (adaptado: se quita la sección "Estado actual del repositorio" sobre convivencia con zona legacy, ya que esta plantilla nace 100% hexagonal, sin `modules_legacy/`/`routers/`/`services/`)

```markdown
# Arquitectura

## Regla de dependencias (obligatoria)

```
infrastructure → application → domain
bootstrap     → infrastructure / application
```

- `domain/` — entidades y reglas de negocio. Cero imports de FastAPI, Motor, Mongo, SDKs cloud.
- `application/` — casos de uso, DTOs, puertos (ABC). Sin frameworks de transporte o persistencia.
- `infrastructure/` — implementa puertos. Aqui vive FastAPI, Motor, adaptadores externos.
- `bootstrap.py` — conecta concretos, expone `register_module(app)`.

## Estructura de un módulo

```text
modules/<modulo>/
  application/
    dto/
    ports/           ← ABCs: XxxRepositoryPort
    services/        ← CrearXxxService, ListarXxxService …
  domain/
    entities.py (o entities/)
    errors.py
  infrastructure/
    api/
      dependencies.py
      routes.py
      schemas.py
    persistence/
      mongo/
        xxx_repository.py
  bootstrap.py
```

Ejemplo completo y funcional: `modules/tareas/`.

## ¿Qué va en `shared/`?

Sí → lo usan varios módulos, no pertenece a un dominio, es infraestructura común.
No → resuelve reglas de un único dominio, solo existe para un módulo puntual.

## Anti-patrones

- Lógica de negocio dentro de rutas FastAPI
- `application/` invocando repositorio concreto (saltarse el puerto)
- `domain/` importando Motor, FastAPI o cualquier SDK externo
- Subir algo a `shared/` "por si acaso"
- Crear `__init__.py` — el proyecto usa namespace packages (Python 3.3+)
```

- [ ] **Step 2: Crear `.claude/CONVENTIONS.md`** (sin cambios de fondo respecto al original de `UltimateBackend`)

```markdown
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

Viven en `domain/errors.py`, heredan de `shared.domain.errors.DomainError`. Lanzados por servicios de aplicación, convertidos a respuestas HTTP por `shared/infrastructure/api/error_handlers.py`.

## Sin `__init__.py`

El proyecto usa namespace packages de Python 3.3+. No crear `__init__.py` en ningún directorio de módulo.
```

- [ ] **Step 3: Crear `.claude/STACK.md`** (adaptado: refleja el patrón singleton `mongo_manager` realmente implementado, en vez del `Depends(get_mongo_db)` aspiracional; agrega arranque local con docker-compose y nota de despliegue)

```markdown
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
```

- [ ] **Step 4: Crear `.claude/TEMPLATE.md`** (adaptado: se quita la dependencia de Moon Modeler y la creación de `.claude/modules/<MODULO>.md`, ya que esta plantilla no incluye esa herramienta ni esa carpeta)

```markdown
# Nuevo módulo — checklist de construcción

> Este checklist cubre la **Fase 3: Construcción**.
> Antes de empezar aquí, seguir el flujo completo en `.claude/WORKFLOW.md`.

---

## Fase 0 — Antes de construir (verificar que está hecho)

- [ ] Alcance acordado (Fase 0 de WORKFLOW.md)
- [ ] Schema Mongo diseñado siguiendo `.claude/MONGODB_MODELING.md` (Fase 1)
- [ ] Diseño de dominio y servicios aprobado (Fase 2)

---

## 1. Definir el dominio

- [ ] Nombre del módulo en snake_case: `modules/<nombre_modulo>/`
- [ ] Límite de dominio claro (qué responsabilidades incluye y excluye)
- [ ] Identificar entidad principal

## 2. Domain

```
modules/<modulo>/domain/
  entities.py               ← clase Python pura (dataclass), sin Pydantic ni Motor
  errors.py                 ← excepciones que heredan de shared.domain.errors.DomainError
```

- [ ] Entidad principal modelada en `domain/entities.py`
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
- [ ] Tests unitarios creados para cada servicio (repositorio mockeado)

## 4. Infrastructure

```
modules/<modulo>/infrastructure/
  api/
    routes.py               ← router = APIRouter(prefix="/api/xxx", tags=["xxx"])
    schemas.py               ← XxxRequest, XxxResponse (Pydantic)
    dependencies.py           ← get_xxx_service() → XxxService(MongoXxxRepository())
  persistence/
    mongo/
      xxx_repository.py      ← MongoXxxRepository(XxxRepositoryPort), usa mongo_manager
```

- [ ] Repositorio concreto implementa el puerto, usando `mongo_manager.get_database()`
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
- [ ] Registrado en `shared/bootstrap/application.py` (import + llamada dentro de `create_app()`)

## Decisión: ¿módulo o shared?

- Solo aplica a un dominio → `modules/<modulo>/`
- Lo usan varios módulos → evaluar `shared/`
- Integración externa reutilizable → normalmente `shared/infrastructure/`

Referencia completa y funcional de todo este checklist: `modules/tareas/`.
```

- [ ] **Step 5: Crear `.claude/TESTING.md`** (sin cambios de fondo)

```markdown
# Testing

## Regla principal

Todo cambio de negocio o de aplicación debe incluir pruebas unitarias. Sin excepción documentada explícita.

## Estructura de carpetas

```text
tests/
  unit/
    modules/
      <modulo>/
        domain/
        application/
          services/
            test_crear_xxx.py
        infrastructure/
    shared/
      application/
      domain/
      infrastructure/
  conftest.py
```

`tests/unit/` espeja `modules/` y `shared/`. Las pruebas no viven dentro de los módulos.

## Qué testear con prioridad

1. `domain/` — entidades, reglas de negocio, errores de dominio
2. `application/services/` — casos de uso, lógica de orquestación
3. `infrastructure/` — solo si hay lógica no trivial en mapeos (ej. `_doc_a_entidad`)

## Qué NO mockear

- Lógica propia del módulo
- Reglas de dominio

## Qué SÍ mockear / no depender de

- MongoDB real
- Servicios externos (GCP Secret Manager, llamadas a otros Cloud Run)

Los repositorios se mockean con `AsyncMock`/`MagicMock` o implementaciones en memoria en pruebas unitarias de `application/`.

## Convención de nombres

```
test_<componente>.py          → archivo
test_<comportamiento>         → función de test
```

## Patrón de test de servicio

```python
# tests/unit/modules/xxx/application/services/test_crear_xxx.py
from unittest.mock import AsyncMock

import pytest

from modules.xxx.application.services.crear_xxx import CrearXxxService
from modules.xxx.application.dto.crear_xxx_dto import CrearXxxDTO


@pytest.fixture
def repositorio_mock():
    return AsyncMock()


async def test_crear_xxx_guarda_entidad(repositorio_mock):
    service = CrearXxxService(repositorio_mock)
    await service.ejecutar(CrearXxxDTO(nombre="test"))
    repositorio_mock.guardar.assert_called_once()
```

Referencia completa y funcional: `tests/unit/modules/tareas/`.
```

- [ ] **Step 6: Crear `.claude/WORKFLOW.md`** (adaptado: se quita la validación en Moon Modeler y la referencia a `MOONMODELER.md`, ya que esta plantilla no incluye esa herramienta)

```markdown
# Flujo de trabajo — Módulo nuevo con Claude

Cómo construir un módulo desde cero correctamente.
**Regla de oro: no avanzar a la siguiente fase sin aprobar la anterior.**

---

## Fase 0 — Definición de alcance

El desarrollador describe el requerimiento. Claude hace preguntas hasta poder responder:

| Pregunta | Por qué importa |
|---|---|
| ¿Cuál es la entidad principal? | Define el límite del módulo |
| ¿Qué campos son obligatorios desde el día uno? | Evita migraciones innecesarias |
| ¿Tiene estados? ¿Cuáles? ¿Transiciones válidas? | Decide si necesita historial |
| ¿Qué servicios incluye este alcance? (lista concreta) | Evita scope creep durante la construcción |
| ¿Con qué otros módulos se relaciona? | Define referencias y desnormalización |
| ¿Hay algo en `shared/` que ya resuelva parte del problema? | Evita duplicar lógica transversal |

**Salida:** alcance escrito y acordado antes de continuar.

---

## Fase 1 — Modelado MongoDB

Con el alcance claro, diseñar la colección **antes de escribir código**,
usando `.claude/MONGODB_MODELING.md` como guía:

1. Estructura del documento (campos, tipos, obligatorios/opcionales)
2. Qué se embebe y qué se referencia (con justificación)
3. Patrón de auditoría (`creado_por` / `actualizado_por`)
4. Historial de estados (si aplica)
5. Índices para las consultas principales

El desarrollador valida el modelo propuesto por escrito antes de continuar.

**Salida:** schema confirmado (estructura + índices). No hay código hasta aquí.

---

## Fase 2 — Diseño de dominio y servicios

Con el schema aprobado, Claude propone:

1. Entidad de dominio — campos, tipos
2. Puerto de repositorio — métodos abstractos necesarios
3. Lista de servicios — nombre, input, output, reglas de negocio
4. Errores de dominio posibles

Claude presenta el diseño completo para revisión. **Aún no escribe código.**

**Salida:** plan aprobado por el desarrollador.

---

## Fase 3 — Construcción

Con el plan aprobado, construir siguiendo el orden de `.claude/TEMPLATE.md`:

```
domain/         ← entidad + errores
application/    ← DTOs + puerto + servicios + tests
infrastructure/ ← repositorio + rutas + dependencies
bootstrap.py    ← register_module()
```

Tests unitarios se escriben junto a cada servicio, no al final.

---

## Fase 4 — Cierre (antes del PR)

Recorrer `.claude/SOLID_CHECKLIST.md` completo.

---

## Referencia rápida

| Fase | Archivo de apoyo |
|---|---|
| Modelado Mongo | `.claude/MONGODB_MODELING.md` |
| Construcción de consultas | `.claude/MONGODB_QUERIES.md` |
| Estructura de archivos | `.claude/TEMPLATE.md` |
| Checklist pre-PR | `.claude/SOLID_CHECKLIST.md` |
| Convenciones de nombres | `.claude/CONVENTIONS.md` |
```

- [ ] **Step 7: Crear `.claude/SOLID_CHECKLIST.md`** (adaptado: se quita la referencia a Moon Modeler y al script de sync `--dry-run`, ya que no forman parte de esta plantilla)

```markdown
# Checklist antes de PR

## Arquitectura

- [ ] `domain/` no importa FastAPI, Motor ni SDKs externos
- [ ] `application/` no importa frameworks de transporte o persistencia
- [ ] Los servicios dependen de puertos (ABCs), no de repositorios concretos
- [ ] La ruta FastAPI solo traduce HTTP → delega al servicio → devuelve respuesta
- [ ] No se crearon `__init__.py`

## Ubicación de código

- [ ] Lógica de negocio en `domain/` o `application/`, no en rutas
- [ ] Schemas HTTP en `infrastructure/api/schemas.py`
- [ ] Mapeo Mongo en el repositorio (o `xxx_mapper.py` si es grande)
- [ ] Antes de duplicar algo, revisé `shared/`

## API

- [ ] Cada endpoint tiene `summary=` (verbo en tercera persona)
- [ ] `responses=` documenta los errores 4xx de negocio relevantes
- [ ] No hay lógica de negocio en los handlers
- [ ] Los errores de dominio se capturan antes de llegar al cliente como 500

## MongoDB

- [ ] Índices responden a consultas concretas (prefijo `idx_`/`uq_`/`ttl_`)
- [ ] Pipeline tiene `$match` al inicio

## Tests

- [ ] Cada servicio nuevo o modificado tiene prueba unitaria
- [ ] Si se corrigió un bug: hay prueba que reproduce el caso
- [ ] Las pruebas no dependen de Mongo real
- [ ] Archivos de test en `tests/unit/modules/<modulo>/...`

## Módulo

- [ ] Si el módulo es nuevo: `register_module(app)` implementado y registrado
```

- [ ] **Step 8: Crear `.claude/API.md`** (adaptado: el ejemplo de `dependencies.py` refleja el patrón singleton `mongo_manager` en vez de `Depends(get_mongo_db)`)

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
) -> XxxResponse:
    resultado = await service.ejecutar(CrearXxxDTO(...))
    return XxxResponse(...)
```

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

Los errores de dominio (`DomainError` y subclases) se capturan globalmente
en `shared/infrastructure/api/error_handlers.py` y se convierten a
`JSONResponse(status_code=exc.status_code, content={"detail": exc.mensaje})`.
No deben llegar al cliente como errores 500.
```

- [ ] **Step 9: Crear `.claude/MONGODB.md`** (adaptado: se documenta explícitamente que el framework de `MongoCollectionDefinition`/`registry.py`/script de sync de `UltimateBackend` **no** está incluido en esta plantilla base)

```markdown
# MongoDB

## Alcance de esta plantilla

Esta plantilla **no** incluye el framework de `MongoCollectionDefinition` /
`registry.py` / script `sync_schema --dry-run` que usa `UltimateBackend`. Los
repositorios de esta plantilla (ver `modules/tareas/infrastructure/persistence/mongo/`)
acceden directo a la colección vía `mongo_manager.get_database()[...]`, sin
una capa de definición/registro de schema.

Si un proyecto concreto necesita ese nivel de gobierno de schema (validators
versionados, sincronización automática, Moon Modeler), se porta desde
`ms-continuum`/`UltimateBackend` como una adición deliberada, no se asume
disponible por defecto.

## Convenciones de índices (sí aplican siempre)

- `idx_` prefijo para índices normales
- `uq_` prefijo para índices únicos
- `ttl_` prefijo para índices de expiración (TTL)
- Cada índice responde a una consulta o restricción concreta, no a intuición
- Definir índices desde el diseño inicial, no cuando ya hay lentitud en producción

## Checklist antes de nueva colección

- [ ] Campos obligatorios/opcionales definidos
- [ ] Identificador natural identificado (¿debe ser único?)
- [ ] Índices responden a consultas reales
- [ ] Mapeo `_doc_a_entidad`/`_entidad_a_doc` implementado en el repositorio
```

- [ ] **Step 10: Crear `.claude/MONGODB_MODELING.md`** (sin cambios de fondo; los ejemplos de dominio ilustran el patrón general y no requieren que el módulo exista en esta plantilla)

```markdown
# MongoDB — Modelado de colecciones

Usar este archivo cuando el usuario describe un requerimiento o historia de usuario y necesita diseñar una colección nueva.

---

## Proceso antes de escribir código

1. Identificar la entidad principal y su límite de dominio
2. Definir campos obligatorios vs opcionales desde el día uno
3. Decidir qué se embebe y qué se referencia
4. Identificar si necesita estado → historial
5. Definir las consultas principales → índices
6. Evaluar si algún array puede crecer sin límite
7. Definir el identificador natural (si existe)

---

## Patrón de auditoría — `creado_por` / `actualizado_por`

**Siempre** en lugar de `created_at` / `updated_at` / `created_by_id`.

```python
class AuditPersona(BaseDomainEntity):
    id_persona: str
    nombre: str       # desnormalizado para evitar lookup en lectura
    fecha: datetime
```

**Por qué `nombre` embebido:** permite mostrar "Creado por Ana García el 12/06/2026" sin join. El nombre puede quedar desactualizado si la persona lo cambia — aceptable para auditoría.

---

## Embeber vs referenciar

### Embeber cuando:
- El subdocumento **siempre se lee junto al padre**
- El array **tiene límite razonable**
- El dato es **propiedad exclusiva** del documento padre
- Necesitas **atomicidad** en escritura

### Referenciar cuando:
- El dato **existe y se consulta independientemente**
- El dato es **compartido** por varios documentos
- El array puede crecer **sin límite previsible**
- La entidad referenciada **cambia con frecuencia**

### Regla general para desnormalizar valores de otra colección

Embeber el valor (además del ID) cuando se cumplen **las tres condiciones**:

| Condición | Ejemplo que la cumple | Ejemplo que NO la cumple |
|---|---|---|
| Se muestra en **listados frecuentes** | Nombre del ponente en lista de eventos | Dirección completa del sitio |
| **Cambia raramente** | Nombre de un rol, nombre de un país | Precio de un producto, saldo de cuenta |
| **La desactualización es aceptable** | Nombre del curso en un registro histórico | Estado actual de un contrato |

Si las tres se cumplen → embeber `{id, nombre}`. Si alguna falla → solo guardar el ID.

---

## Tipos de identificadores

| Tipo | bsonType | Cuándo usarlo |
|---|---|---|
| `_id` | objectId | Siempre, identificador técnico de Mongo |
| Consecutivos de negocio | string / int | Cuando existe un código visible al usuario |

---

## Cuándo un array embebido se convierte en colección propia

Separar en colección cuando se cumpla **al menos uno**:

| Criterio | Ejemplo |
|---|---|
| El array puede crecer **sin límite previsible** | Historial muy activo |
| Los items se consultan **independientemente del padre** | "Dame todos los X del sitio Y este mes" |
| Cada item es un **documento sustancial** por sí solo | Entidad con su propio historial |
| Se necesitan **índices propios** sobre los items | `(id_padre, fecha)` no tiene sentido embebido |

**Señal práctica:** si te encuentras escribiendo un pipeline con `$unwind` para consultar los items del array con frecuencia, probablemente debería ser una colección separada.

## Señales de alerta

- Array embebido que podría tener **cientos de items** → evaluar colección separada
- **Lookup frecuente** de un campo que se muestra siempre → desnormalizar
- Filtro frecuente sobre un campo **sin índice** → agregar índice
- Documento que **supera los 16MB** (límite de Mongo) → rediseñar

---

## Checklist antes de proponer el modelo

- [ ] Identifiqué el identificador técnico y el natural (si existe)
- [ ] Todos los campos obligatorios están definidos
- [ ] `creado_por` y `actualizado_por` incluidos si aplica auditoría
- [ ] Si tiene estados: definí las transiciones válidas y decidí si necesita historial
- [ ] Decidí explícitamente qué se embebe y qué se referencia (y por qué)
- [ ] Identifiqué las consultas principales y propuse índices para cada una
- [ ] Revisé si algún array puede crecer sin límite
```

- [ ] **Step 11: Crear `.claude/MONGODB_QUERIES.md`** (adaptado: se quitan los punteros "Referencia real" a archivos concretos de `UltimateBackend` que no existen en esta plantilla, y se agrega una nota sobre el helper `ConstructorPipelineBase`)

```markdown
# MongoDB — Construcción de consultas y pipelines

## Alcance de esta plantilla

Esta plantilla no incluye un helper tipo `ConstructorPipelineBase`/`.paginar()`
para construir pipelines de agregación — el módulo de ejemplo `tareas` usa
consultas simples (`find().sort()`) porque no las necesita. Las convenciones
de esta página son la guía de referencia para cuando un módulo sí requiera
pipelines de agregación complejos; si la necesidad se repite entre módulos,
portar el helper desde `ms-continuum` como adición deliberada a `shared/`.

---

## Orden canónico de un pipeline

```
1. $match          ← reducir documentos lo antes posible
2. $sort           ← soportado por índice, antes de paginar
3. $lookup         ← solo si ya se redujo el conjunto
4. $addFields      ← enriquecer después del cruce
5. $project        ← recortar campos innecesarios
6. paginación      ← siempre al final
```

La regla de oro: **cada etapa recibe menos documentos que la anterior**.

## $match — reglas

1. Siempre al inicio, lo más pronto posible.
2. Agrupar condiciones en un solo `$match` cuando siempre aplican juntas.
3. Métodos separados que cada uno agrega su propio `$match` condicional son aceptables cuando cada condición es opcional.

## $sort — reglas

1. Siempre respaldado por un índice.
2. Sort antes de `$lookup` y `$project`.
3. Sort estable: incluir `_id` como desempate para paginación consistente.

## $lookup — dos formas

- **Forma simple**: trae todos los campos del documento cruzado. Aceptable solo si la colección es pequeña.
- **Forma con pipeline interno** (preferida): filtra y proyecta dentro del `$lookup`, trae solo lo necesario. Usar cuando la colección cruzada es grande o solo necesitas 1-3 campos.
- Filtrar **antes** del `$lookup` siempre que se pueda.
- Limpiar campos temporales del lookup (`_personas`, `_roles`) con `$project` al final.

## $project — reglas

1. Proyectar pronto para reducir el tamaño de documentos.
2. Calcular campos derivados en el `$project` (`$size`, `$filter`) en vez de en Python.
3. Usar `$ifNull` para campos opcionales.

## Anti-patrones

| Anti-patrón | Problema | Solución |
|---|---|---|
| `$lookup` sin pipeline interno sobre colección grande | Trae todos los campos de todos los docs cruzados | Usar forma `let/pipeline` con `$project` interno |
| `$sort` sin índice sobre muchos documentos | Sort en memoria, costoso | Asegurar que el campo tenga índice |
| `$match` después de `$lookup` sobre campo del doc principal | El lookup ya procesó más docs de los necesarios | Mover el `$match` antes del `$lookup` |
| Múltiples `$match` seguidos incondicionales | Difícil de razonar | Construir un solo dict de condiciones |
| Calcular longitud de arrays en Python después de la consulta | Trae el array entero por red | Usar `{"$size": "$campo"}` en `$project` |
```

- [ ] **Step 12: Crear `CLAUDE.md` en la raíz** (adaptado: se quitan las filas de `MOONMODELER.md` y `modules/` de negocio, ya que no aplican a esta plantilla)

```markdown
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
```

- [ ] **Step 13: Verificar que todas las rutas referenciadas en `CLAUDE.md` existen**

Run: `python -c "import pathlib; base = pathlib.Path('.'); rutas = ['.claude/WORKFLOW.md','.claude/ARCHITECTURE.md','.claude/STACK.md','.claude/CONVENTIONS.md','.claude/API.md','.claude/MONGODB.md','.claude/MONGODB_MODELING.md','.claude/MONGODB_QUERIES.md','.claude/TESTING.md','.claude/TEMPLATE.md','.claude/SOLID_CHECKLIST.md']; faltantes = [r for r in rutas if not (base / r).exists()]; print('Faltantes:', faltantes) if faltantes else print('OK: todas las rutas existen')"`
Expected: `OK: todas las rutas existen`

- [ ] **Step 14: Commit**

```bash
git add CLAUDE.md .claude/
git commit -m "docs: adaptar convenciones .claude/*.md desde UltimateBackend"
```

---

## Task 17: `docs/arquitectura_hexagonal.md` — adaptación desde `UltimateBackend`

**Files:**
- Create: `docs/arquitectura_hexagonal.md`

**Interfaces:**
- Ninguna interfaz de código. Verificación: el archivo existe y no contiene referencias a módulos de negocio específicos de CEMP ni a Moon Modeler.

- [ ] **Step 1: Leer el archivo fuente completo**

Run (desde un agente con acceso de lectura a `ia-codice`/`proyectos`): leer íntegro `C:\Users\FIMLM\Documents\proyectos\UltimateBackend\docs\arquitectura_hexagonal.md`.

- [ ] **Step 2: Copiar el contenido a `docs/arquitectura_hexagonal.md` y aplicar las siguientes ediciones**

Reglas de adaptación (aplicar todas):
1. Eliminar cualquier párrafo o sección que mencione por nombre alguno de estos módulos de negocio de CEMP: `encuestas`, `cursos`, `labores`, `parametrizacion`, `usuarios`, `terceros`, `sitios`, `soporte`, `libreria`. Si un párrafo usa uno de estos solo como ejemplo ilustrativo de un concepto general (no como referencia a código real del repo), puede quedar reemplazando el nombre del módulo de negocio por `tareas` (el módulo de ejemplo de esta plantilla) para mantener la coherencia.
2. Eliminar cualquier mención a "Moon Modeler"/`.dmm`.
3. Eliminar cualquier sección que describa la convivencia con código legacy (`modules_legacy/`, `routers/`, `services/`, `db/`) — esta plantilla nace 100% hexagonal.
4. Mantener intacta toda explicación genérica de: las tres capas (`domain`/`application`/`infrastructure`), la regla de dependencias, el rol de `bootstrap.py`, y la justificación/rationale de por qué se eligió arquitectura hexagonal.
5. Si el documento tiene ejemplos de código de módulos de negocio de CEMP, reemplazarlos por fragmentos equivalentes de `modules/tareas/` (ya construido en Tasks 10-12 de este plan) cuando sea directo hacerlo; si no es directo, eliminar el ejemplo y dejar solo la explicación en prosa.

- [ ] **Step 3: Verificar que no quedaron referencias prohibidas**

Run: `python -c "
import pathlib
texto = pathlib.Path('docs/arquitectura_hexagonal.md').read_text(encoding='utf-8').lower()
prohibidos = ['encuestas', 'cursos', 'labores', 'parametrizacion', 'terceros', 'moon modeler', 'modules_legacy']
encontrados = [p for p in prohibidos if p in texto]
print('Encontrados:', encontrados) if encontrados else print('OK: sin referencias prohibidas')
"`
Expected: `OK: sin referencias prohibidas`

- [ ] **Step 4: Commit**

```bash
git add docs/arquitectura_hexagonal.md
git commit -m "docs: adaptar arquitectura_hexagonal.md desde UltimateBackend"
```

---

## Verificación final del plan completo

- [ ] **Ejecutar toda la suite de tests**

Run: `pytest -v`
Expected: PASS — todos los tests de Tasks 1-13 (dominio, aplicación, infraestructura, bootstrap y wiring del módulo `tareas`, más toda la infraestructura compartida de Mongo/Secret Manager/Cloud Run/autenticación)

- [ ] **Levantar el entorno local completo y probar manualmente**

Run: `docker compose up -d mongo && python main.py`
Expected: `POST /api/tareas` y `GET /api/tareas` funcionan de punta a punta contra Mongo real local

- [ ] **Validar `cloudbuild.yaml`**

Run: `python -c "import yaml; yaml.safe_load(open('cloudbuild.yaml', encoding='utf-8')); print('OK')"`
Expected: `OK`
