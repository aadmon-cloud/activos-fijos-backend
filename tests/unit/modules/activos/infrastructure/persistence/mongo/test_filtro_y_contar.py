import re
from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from modules.activos.domain.entities import EstadoCicloVida
from modules.activos.infrastructure.persistence.mongo.activo_repository import (
    MongoActivoRepository,
    _construir_filtro,
)

_SIN_FILTROS = dict(
    area_id=None,
    categoria_id=None,
    responsable_id=None,
    condicion_id=None,
    sede_id=None,
    lugar_id=None,
    estado_ciclo_vida=None,
    busqueda=None,
)


def test_sin_filtros_el_filtro_esta_vacio():
    assert _construir_filtro(**_SIN_FILTROS) == {}


def test_los_ids_se_convierten_a_object_id_y_el_estado_a_su_valor():
    area = str(ObjectId())

    filtro = _construir_filtro(
        **{**_SIN_FILTROS, "area_id": area, "estado_ciclo_vida": EstadoCicloVida.PRESTADO}
    )

    assert filtro == {"area_id": ObjectId(area), "estado_ciclo_vida": "prestado"}


def test_la_busqueda_se_escapa_para_no_ejecutarse_como_expresion_regular():
    filtro = _construir_filtro(**{**_SIN_FILTROS, "busqueda": "a.*(b"})

    patron = filtro["$or"][0]["nombre"]["$regex"]
    assert patron == re.escape("a.*(b")
    assert re.search(patron, "xxa.*(bxx")
    assert not re.search(patron, "aXXXb")
    assert len(filtro["$or"]) == 5


async def test_contar_usa_el_mismo_filtro_que_listar():
    area = str(ObjectId())
    coleccion = MagicMock()
    coleccion.count_documents = AsyncMock(return_value=42)
    base = MagicMock()
    base.__getitem__.return_value = coleccion

    with patch(
        "modules.activos.infrastructure.persistence.mongo.activo_repository.mongo_manager"
    ) as manager:
        manager.get_database.return_value = base
        total = await MongoActivoRepository().contar(**{**_SIN_FILTROS, "area_id": area})

    assert total == 42
    coleccion.count_documents.assert_awaited_once_with({"area_id": ObjectId(area)})
