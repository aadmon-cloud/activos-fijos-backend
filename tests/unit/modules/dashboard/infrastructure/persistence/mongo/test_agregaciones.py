from unittest.mock import AsyncMock, MagicMock

from modules.dashboard.infrastructure.persistence.mongo.agregaciones import contar_y_agrupar


def _coleccion_con_resultado(resultado: list[dict]):
    coleccion = MagicMock()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=resultado)
    coleccion.aggregate = MagicMock(return_value=cursor)
    return coleccion


async def test_contar_y_agrupar_retorna_cero_y_vacio_sobre_coleccion_vacia():
    coleccion = _coleccion_con_resultado([])

    total, agrupados = await contar_y_agrupar(coleccion, "estado")

    assert total == 0
    assert agrupados == {"estado": {}}


async def test_contar_y_agrupar_arma_el_total_y_los_grupos():
    coleccion = _coleccion_con_resultado(
        [
            {
                "total": [{"cantidad": 7}],
                "estado": [
                    {"_id": "pendiente", "cantidad": 3},
                    {"_id": "resuelta", "cantidad": 4},
                ],
            }
        ]
    )

    total, agrupados = await contar_y_agrupar(coleccion, "estado")

    assert total == 7
    assert agrupados == {"estado": {"pendiente": 3, "resuelta": 4}}


async def test_contar_y_agrupar_ignora_grupos_con_id_nulo():
    coleccion = _coleccion_con_resultado(
        [{"total": [{"cantidad": 2}], "tipo": [{"_id": None, "cantidad": 2}]}]
    )

    total, agrupados = await contar_y_agrupar(coleccion, "tipo")

    assert total == 2
    assert agrupados == {"tipo": {}}


async def test_contar_y_agrupar_soporta_varios_campos():
    coleccion = _coleccion_con_resultado(
        [
            {
                "total": [{"cantidad": 5}],
                "tipo": [{"_id": "prestamo", "cantidad": 5}],
                "estado": [{"_id": "solicitado", "cantidad": 5}],
            }
        ]
    )

    total, agrupados = await contar_y_agrupar(coleccion, "tipo", "estado")

    assert total == 5
    assert agrupados["tipo"] == {"prestamo": 5}
    assert agrupados["estado"] == {"solicitado": 5}
