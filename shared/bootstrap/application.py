from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from config.logger import configurar_logging
from modules.activos.bootstrap import register_module as register_module_activos
from modules.activos.infrastructure.persistence.mongo.activo_repository import (
    crear_indices as crear_indices_activos,
)
from modules.activos.infrastructure.persistence.mongo.historial_activo_repository import (
    crear_indices as crear_indices_activos_historial,
)
from modules.catalogos.bootstrap import register_module as register_module_catalogos
from modules.catalogos.infrastructure.persistence.mongo.area_repository import (
    crear_indices as crear_indices_areas,
)
from modules.catalogos.infrastructure.persistence.mongo.categoria_repository import (
    crear_indices as crear_indices_categorias,
)
from modules.catalogos.infrastructure.persistence.mongo.condicion_repository import (
    crear_indices as crear_indices_condiciones,
)
from modules.catalogos.infrastructure.persistence.mongo.lugar_repository import (
    crear_indices as crear_indices_lugares,
)
from modules.catalogos.infrastructure.persistence.mongo.sede_repository import (
    crear_indices as crear_indices_sedes,
)
from modules.solicitudes.bootstrap import register_module as register_module_solicitudes
from modules.solicitudes.infrastructure.persistence.mongo.solicitud_repository import (
    crear_indices as crear_indices_solicitudes,
)
from modules.tareas.bootstrap import register_module as register_module_tareas
from modules.usuarios.bootstrap import register_module as register_module_usuarios
from modules.usuarios.infrastructure.persistence.mongo.usuario_repository import (
    crear_indices as crear_indices_usuarios,
)
from shared.infrastructure.api.error_handlers import register_error_handlers
from shared.infrastructure.persistence.mongo.database import mongo_manager

configurar_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    mongo_manager.connect()
    await crear_indices_usuarios()
    await crear_indices_areas()
    await crear_indices_categorias()
    await crear_indices_condiciones()
    await crear_indices_sedes()
    await crear_indices_lugares()
    await crear_indices_activos()
    await crear_indices_activos_historial()
    await crear_indices_solicitudes()
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
    register_module_tareas(app)
    register_module_usuarios(app)
    register_module_catalogos(app)
    register_module_activos(app)
    register_module_solicitudes(app)

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
