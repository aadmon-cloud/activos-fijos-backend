from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from config.logger import configurar_logging
from modules.aprobaciones_pendientes.bootstrap import (
    register_module as register_module_aprobaciones_pendientes,
)
from modules.auth.bootstrap import register_module as register_module_auth
from modules.ejemplo_tareas.bootstrap import register_module as register_module_ejemplo_tareas
from modules.inventario_reportes.bootstrap import (
    register_module as register_module_inventario_reportes,
)
from modules.mercados_predefinidos.bootstrap import (
    register_module as register_module_mercados_predefinidos,
)
from modules.movimientos.bootstrap import register_module as register_module_movimientos
from modules.productos.bootstrap import register_module as register_module_productos
from modules.reservas.bootstrap import register_module as register_module_reservas
from modules.ubicaciones.bootstrap import register_module as register_module_ubicaciones
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
    register_module_auth(app)
    register_module_ejemplo_tareas(app)
    register_module_productos(app)
    register_module_ubicaciones(app)
    register_module_mercados_predefinidos(app)
    register_module_reservas(app)
    register_module_movimientos(app)
    register_module_aprobaciones_pendientes(app)
    register_module_inventario_reportes(app)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/")
    async def backend():
        return {
            "backend": "Template FastAPI activo. Base hexagonal lista para extender."
        }

    @app.get("/redoc", include_in_schema=False)
    async def redoc():
        return get_redoc_html(
            openapi_url="/openapi.json",
            title="Documentacion ReDoc",
            redoc_js_url="https://cdn.jsdelivr.net/npm/redoc/bundles/redoc.standalone.js",
        )

    return app
