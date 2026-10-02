from unittest.mock import AsyncMock, MagicMock

from modules.productos.infrastructure.persistence.mongo.producto_repository import (
    MongoProductoRepository,
)


def _db_falsa():
    coleccion = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[])
    coleccion.find = MagicMock(return_value=cursor)
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coleccion)
    return db, coleccion


async def test_buscar_por_texto_escapa_metacaracteres_de_regex():
    """Regresión: el legacy pasaba el término de búsqueda directo a `$regex` sin
    escapar, permitiendo inyectar metacaracteres de regex (riesgo de ReDoS)."""
    db, coleccion = _db_falsa()
    repo = MongoProductoRepository(db)

    await repo.buscar_por_texto("(.*)+")

    filtro = coleccion.find.call_args.args[0]
    patrones = [condicion[campo]["$regex"] for condicion in filtro["$or"] for campo in condicion]
    assert all(patron == r"\(\.\*\)\+" for patron in patrones)


async def test_buscar_por_texto_busca_en_nombre_codigo_y_descripcion():
    db, coleccion = _db_falsa()
    repo = MongoProductoRepository(db)

    await repo.buscar_por_texto("laptop")

    filtro = coleccion.find.call_args.args[0]
    campos_buscados = {campo for condicion in filtro["$or"] for campo in condicion}
    assert campos_buscados == {"nombre", "codigo", "descripcion"}


async def test_listar_bajo_stock_usa_expr_comparando_stock_actual_y_minimo():
    db, coleccion = _db_falsa()
    repo = MongoProductoRepository(db)

    await repo.listar_bajo_stock()

    filtro = coleccion.find.call_args.args[0]
    assert filtro == {"$expr": {"$lt": ["$stock_actual", "$stock_minimo"]}}


async def test_calcular_valor_total_usa_pipeline_de_agregacion_con_group_y_sum():
    coleccion = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[{"_id": None, "valor_total": 1234.5}])
    coleccion.aggregate = MagicMock(return_value=cursor)
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coleccion)
    repo = MongoProductoRepository(db)

    resultado = await repo.calcular_valor_total()

    pipeline = coleccion.aggregate.call_args.args[0]
    assert pipeline == [
        {
            "$group": {
                "_id": None,
                "valor_total": {"$sum": {"$multiply": ["$stock_actual", "$precio_unitario"]}},
            }
        }
    ]
    assert resultado == 1234.5


async def test_calcular_valor_total_devuelve_cero_sin_productos():
    coleccion = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[])
    coleccion.aggregate = MagicMock(return_value=cursor)
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coleccion)
    repo = MongoProductoRepository(db)

    resultado = await repo.calcular_valor_total()

    assert resultado == 0.0
