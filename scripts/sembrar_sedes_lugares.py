"""Siembra las sedes y lugares iniciales (dato nuevo, no es migracion desde el legado).

Crea las sedes Prado y Bosa, y en cada una los lugares de tipo bodega, bano y exterior.
Los espacios comunes y las oficinas (~10 y ~20 respectivamente) se cargan despues desde
la API por un administrador, no por este script.

Es idempotente: si una sede o lugar ya existe (mismo nombre), se omite.

Uso:
    python -m scripts.sembrar_sedes_lugares
"""

import asyncio

from config.logger import configurar_logging
from modules.catalogos.application.dto.crear_lugar_dto import CrearLugarDTO
from modules.catalogos.application.dto.crear_sede_dto import CrearSedeDTO
from modules.catalogos.application.services.crear_lugar import CrearLugarService
from modules.catalogos.application.services.crear_sede import CrearSedeService
from modules.catalogos.domain.entities import TipoLugar
from modules.catalogos.domain.errors import LugarNombreDuplicadoError, SedeNombreDuplicadoError
from modules.catalogos.infrastructure.persistence.mongo.lugar_repository import (
    MongoLugarRepository,
)
from modules.catalogos.infrastructure.persistence.mongo.sede_repository import (
    MongoSedeRepository,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

_CREADO_POR_ID = "siembra-inicial"
_CREADO_POR_NOMBRE = "Siembra inicial de catalogos"

_SEDES = ["Prado", "Bosa"]
_LUGARES_INICIALES = [
    ("Bodega", TipoLugar.BODEGA),
    ("Bano", TipoLugar.BANO),
    ("Exterior", TipoLugar.EXTERIOR),
]


async def _sembrar() -> None:
    sede_repository = MongoSedeRepository()
    lugar_repository = MongoLugarRepository()
    crear_sede = CrearSedeService(sede_repository)
    crear_lugar = CrearLugarService(lugar_repository, sede_repository)

    for nombre_sede in _SEDES:
        try:
            sede = await crear_sede.ejecutar(
                CrearSedeDTO(
                    nombre=nombre_sede,
                    creado_por_id=_CREADO_POR_ID,
                    creado_por_nombre=_CREADO_POR_NOMBRE,
                )
            )
            print(f"  sede creada: {nombre_sede}")
        except SedeNombreDuplicadoError:
            sede_existente = await sede_repository.obtener_por_nombre(nombre_sede)
            sede = sede_existente
            print(f"  sede ya existia, se omite: {nombre_sede}")

        for nombre_lugar, tipo_lugar in _LUGARES_INICIALES:
            try:
                await crear_lugar.ejecutar(
                    CrearLugarDTO(
                        nombre=nombre_lugar,
                        tipo=tipo_lugar,
                        sede_id=sede.id,
                        creado_por_id=_CREADO_POR_ID,
                        creado_por_nombre=_CREADO_POR_NOMBRE,
                    )
                )
                print(f"    lugar creado: {nombre_lugar} ({nombre_sede})")
            except LugarNombreDuplicadoError:
                print(f"    lugar ya existia, se omite: {nombre_lugar} ({nombre_sede})")


async def _ejecutar() -> None:
    mongo_manager.connect()
    try:
        print("Sembrando sedes y lugares iniciales...")
        await _sembrar()
    finally:
        mongo_manager.close()


if __name__ == "__main__":
    configurar_logging()
    asyncio.run(_ejecutar())
