from fastapi import FastAPI

from modules.permisos.infrastructure.api.dependencies import get_asegurar_permisos_por_defecto_service
from modules.permisos.infrastructure.api.routes import router


def register_module(app: FastAPI) -> None:
    app.include_router(router)


async def asegurar_permisos_iniciales() -> list[str]:
    """Al arrancar, crea la matriz de fabrica de los roles que aun no la tienen. No pisa lo ya editado."""
    return await get_asegurar_permisos_por_defecto_service().ejecutar()
