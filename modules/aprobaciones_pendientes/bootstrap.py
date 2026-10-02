from fastapi import FastAPI

from modules.aprobaciones_pendientes.infrastructure.api.routes import router


def register_module(app: FastAPI) -> None:
    app.include_router(router)
