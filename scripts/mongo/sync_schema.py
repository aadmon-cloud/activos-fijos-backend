import argparse
import asyncio
import logging

from config.logger import configurar_logging
from shared.infrastructure.persistence.mongo.database import mongo_manager
from shared.infrastructure.persistence.mongo.schema.registry import (
    obtener_colecciones_mongo,
)
from shared.infrastructure.persistence.mongo.schema.runner import (
    ResultadoColeccion,
    sincronizar_colecciones,
)

logger = logging.getLogger(__name__)


def _parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sincroniza validators e indices de las colecciones registradas."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo reporta las acciones planeadas, no aplica cambios en MongoDB.",
    )
    parser.add_argument(
        "--only",
        nargs="+",
        default=None,
        metavar="COLECCION",
        help="Limita la sincronizacion a una o mas colecciones por nombre.",
    )
    parser.add_argument(
        "--drop-extra-indexes",
        action="store_true",
        help="Elimina indices existentes en Mongo que no esten declarados en el schema.",
    )
    return parser.parse_args()


def _reportar(resultados: list[ResultadoColeccion], *, dry_run: bool) -> None:
    modo = "DRY-RUN (sin cambios aplicados)" if dry_run else "APLICADO"
    logger.info("=== Sincronizacion de schema Mongo [%s] ===", modo)

    for resultado in resultados:
        logger.info("Coleccion '%s': %s", resultado.nombre, resultado.accion_coleccion)
        for indice in resultado.indices:
            mensaje = "  indice '%s': %s%s"
            detalle = f" -- {indice.detalle}" if indice.detalle else ""
            if indice.accion in ("conflicto", "extra"):
                logger.warning(mensaje, indice.nombre, indice.accion, detalle)
            else:
                logger.info(mensaje, indice.nombre, indice.accion, detalle)


async def _ejecutar() -> None:
    argumentos = _parsear_argumentos()

    mongo_manager.connect()
    try:
        db = mongo_manager.get_database()
        definiciones = obtener_colecciones_mongo()
        resultados = await sincronizar_colecciones(
            db,
            definiciones,
            dry_run=argumentos.dry_run,
            solo=argumentos.only,
            drop_extra_indexes=argumentos.drop_extra_indexes,
        )
        _reportar(resultados, dry_run=argumentos.dry_run)
    finally:
        mongo_manager.close()


def main() -> None:
    configurar_logging()
    asyncio.run(_ejecutar())


if __name__ == "__main__":
    main()
