from fastapi import FastAPI

from modules.catalogos.infrastructure.api.area_routes import router as area_router
from modules.catalogos.infrastructure.api.categoria_routes import router as categoria_router
from modules.catalogos.infrastructure.api.condicion_routes import router as condicion_router
from modules.catalogos.infrastructure.api.lugar_routes import router as lugar_router
from modules.catalogos.infrastructure.api.sede_routes import router as sede_router


def register_module(app: FastAPI) -> None:
    app.include_router(area_router)
    app.include_router(categoria_router)
    app.include_router(condicion_router)
    app.include_router(sede_router)
    app.include_router(lugar_router)
