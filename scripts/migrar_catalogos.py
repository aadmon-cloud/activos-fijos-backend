"""Migra areas, categorias y condiciones (colección legacy `estados`) hacia `catalogos`.

Debe ejecutarse ANTES de `scripts/migrar_usuarios.py` (ver docs/plan_migracion_activos_fijos.md,
seccion 8.3): la migracion de usuarios necesita que las areas ya existan para resolver su `area_id`.

Es idempotente: si un area/categoria/condicion ya fue migrada (mismo nombre), se omite.

Uso:
    python -m scripts.migrar_catalogos

Variables de entorno adicionales (ademas de las que ya usa la app nueva, ej. MONGO_URL/MONGO_DB):
    LEGACY_MONGO_URL   default: mongodb://localhost:27017
    LEGACY_MONGO_DB    default: GESTIONACTIVOSFIJOS
"""

import asyncio

from config.logger import configurar_logging
from modules.catalogos.application.dto.crear_area_dto import CrearAreaDTO
from modules.catalogos.application.dto.crear_categoria_dto import CrearCategoriaDTO
from modules.catalogos.application.dto.crear_condicion_dto import CrearCondicionDTO
from modules.catalogos.application.services.crear_area import CrearAreaService
from modules.catalogos.application.services.crear_categoria import CrearCategoriaService
from modules.catalogos.application.services.crear_condicion import CrearCondicionService
from modules.catalogos.domain.errors import (
    AreaNombreDuplicadoError,
    CategoriaNombreDuplicadaError,
    CondicionNombreDuplicadoError,
)
from modules.catalogos.infrastructure.persistence.mongo.area_repository import (
    MongoAreaRepository,
)
from modules.catalogos.infrastructure.persistence.mongo.categoria_repository import (
    MongoCategoriaRepository,
)
from modules.catalogos.infrastructure.persistence.mongo.condicion_repository import (
    MongoCondicionRepository,
)
from scripts._legacy_db import conectar_legacy
from shared.infrastructure.persistence.mongo.database import mongo_manager

_CREADO_POR_ID = "migracion-legacy"
_CREADO_POR_NOMBRE = "Migracion de datos legacy"


async def _migrar_areas(db_legacy) -> None:
    servicio = CrearAreaService(MongoAreaRepository())
    for doc in db_legacy["areas"].find({}):
        try:
            await servicio.ejecutar(
                CrearAreaDTO(
                    nombre=doc["nombre"],
                    descripcion=doc.get("descripcion"),
                    creado_por_id=_CREADO_POR_ID,
                    creado_por_nombre=_CREADO_POR_NOMBRE,
                )
            )
            print(f"  area migrada: {doc['nombre']}")
        except AreaNombreDuplicadoError:
            print(f"  area ya existia, se omite: {doc['nombre']}")


async def _migrar_categorias(db_legacy) -> None:
    servicio = CrearCategoriaService(MongoCategoriaRepository())
    for doc in db_legacy["categorias"].find({}):
        try:
            await servicio.ejecutar(
                CrearCategoriaDTO(
                    nombre=doc["nombre"],
                    descripcion=doc.get("descripcion"),
                    creado_por_id=_CREADO_POR_ID,
                    creado_por_nombre=_CREADO_POR_NOMBRE,
                )
            )
            print(f"  categoria migrada: {doc['nombre']}")
        except CategoriaNombreDuplicadaError:
            print(f"  categoria ya existia, se omite: {doc['nombre']}")


async def _migrar_condiciones(db_legacy) -> None:
    servicio = CrearCondicionService(MongoCondicionRepository())
    for doc in db_legacy["estados"].find({}):
        try:
            await servicio.ejecutar(
                CrearCondicionDTO(
                    nombre=doc["nombre"],
                    color=doc.get("color", "#000000"),
                    descripcion=doc.get("descripcion"),
                    creado_por_id=_CREADO_POR_ID,
                    creado_por_nombre=_CREADO_POR_NOMBRE,
                )
            )
            print(f"  condicion migrada: {doc['nombre']}")
        except CondicionNombreDuplicadoError:
            print(f"  condicion ya existia, se omite: {doc['nombre']}")


async def _ejecutar() -> None:
    cliente_legacy, db_legacy = conectar_legacy()
    mongo_manager.connect()
    try:
        print("Migrando areas...")
        await _migrar_areas(db_legacy)
        print("Migrando categorias...")
        await _migrar_categorias(db_legacy)
        print("Migrando condiciones (coleccion legacy 'estados')...")
        await _migrar_condiciones(db_legacy)
    finally:
        mongo_manager.close()
        cliente_legacy.close()


if __name__ == "__main__":
    configurar_logging()
    asyncio.run(_ejecutar())
