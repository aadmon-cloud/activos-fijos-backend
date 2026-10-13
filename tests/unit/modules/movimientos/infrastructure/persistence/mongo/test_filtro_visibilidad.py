from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from modules.movimientos.application.ports.movimiento_repository import (
    ParaMiMovimiento,
    VisibilidadMovimiento,
)
from modules.movimientos.domain.entities import EstadoMovimiento, TipoMovimiento
from modules.movimientos.infrastructure.persistence.mongo.movimiento_repository import (
    MongoMovimientoRepository,
    _construir_filtro,
)

_MODULO = "modules.movimientos.infrastructure.persistence.mongo.movimiento_repository"

_SIN_FILTROS = dict(
    tipo=None,
    estado=None,
    activo_id=None,
    usuario_destino_id=None,
    creado_por_id=None,
    visible_para=None,
    para_mi=None,
)


def test_sin_filtros_el_filtro_esta_vacio():
    assert _construir_filtro(**_SIN_FILTROS) == {}


def test_los_filtros_se_convierten_a_su_representacion_en_mongo():
    activo, destino = str(ObjectId()), str(ObjectId())

    filtro = _construir_filtro(
        **{
            **_SIN_FILTROS,
            "tipo": TipoMovimiento.PRESTAMO,
            "estado": EstadoMovimiento.EN_CURSO,
            "activo_id": activo,
            "usuario_destino_id": destino,
            "creado_por_id": "u1",
        }
    )

    assert filtro == {
        "tipo": "prestamo",
        "estado": "en_curso",
        "items.activo_id": ObjectId(activo),
        "usuario_destino_id": ObjectId(destino),
        "creado_por.id_persona": "u1",
    }


def test_la_visibilidad_incluye_lo_creado_el_destino_el_responsable_original_y_los_activos_a_cargo():
    actor, activo_a, activo_b = str(ObjectId()), str(ObjectId()), str(ObjectId())

    filtro = _construir_filtro(
        **{**_SIN_FILTROS, "visible_para": VisibilidadMovimiento(actor, frozenset({activo_a, activo_b}))}
    )

    condiciones = filtro["$and"][0]["$or"]
    assert condiciones[:3] == [
        {"creado_por.id_persona": actor},
        {"usuario_destino_id": ObjectId(actor)},
        {"items.responsable_original_id": ObjectId(actor)},
    ]
    assert set(condiciones[3]["items.activo_id"]["$in"]) == {ObjectId(activo_a), ObjectId(activo_b)}


def test_sin_activos_a_cargo_la_visibilidad_no_incluye_la_condicion_de_activos():
    actor = str(ObjectId())

    filtro = _construir_filtro(**{**_SIN_FILTROS, "visible_para": VisibilidadMovimiento(actor, frozenset())})

    condiciones = filtro["$and"][0]["$or"]
    assert len(condiciones) == 3
    assert all("items.activo_id" not in condicion for condicion in condiciones)


def test_la_visibilidad_se_combina_con_los_demas_filtros_sin_reemplazarlos():
    actor = str(ObjectId())

    filtro = _construir_filtro(
        **{
            **_SIN_FILTROS,
            "estado": EstadoMovimiento.SOLICITADO,
            "visible_para": VisibilidadMovimiento(actor, frozenset()),
        }
    )

    assert filtro["estado"] == "solicitado"
    assert "$and" in filtro


def test_para_mi_incluye_destinatario_responsable_original_y_activos_a_cargo():
    actor, activo = str(ObjectId()), str(ObjectId())

    filtro = _construir_filtro(**{**_SIN_FILTROS, "para_mi": ParaMiMovimiento(actor, frozenset({activo}), False)})

    condiciones = filtro["$and"][0]["$or"]
    assert condiciones[0] == {"usuario_destino_id": ObjectId(actor)}
    assert condiciones[1] == {"items.responsable_original_id": ObjectId(actor)}
    assert condiciones[2] == {"items.activo_id": {"$in": [ObjectId(activo)]}}
    assert len(condiciones) == 3


def test_para_mi_del_administrador_incluye_lo_que_espera_su_accion():
    actor = str(ObjectId())

    filtro = _construir_filtro(**{**_SIN_FILTROS, "para_mi": ParaMiMovimiento(actor, frozenset(), True)})

    condiciones = filtro["$and"][0]["$or"]
    assert {"items.estado": {"$in": ["pendiente_admin", "devolucion_solicitada"]}} in condiciones


def test_la_visibilidad_y_para_mi_se_aplican_las_dos_a_la_vez():
    actor = str(ObjectId())

    filtro = _construir_filtro(
        **{
            **_SIN_FILTROS,
            "visible_para": VisibilidadMovimiento(actor, frozenset()),
            "para_mi": ParaMiMovimiento(actor, frozenset(), False),
        }
    )

    assert len(filtro["$and"]) == 2


@patch(f"{_MODULO}.mongo_manager")
async def test_contar_usa_el_mismo_filtro_que_listar(mongo_manager_mock):
    coleccion = MagicMock()
    coleccion.count_documents = AsyncMock(return_value=4)
    mongo_manager_mock.get_database.return_value = {"movimientos": coleccion}
    visible = VisibilidadMovimiento(str(ObjectId()), frozenset())

    total = await MongoMovimientoRepository().contar(**{**_SIN_FILTROS, "visible_para": visible})

    assert total == 4
    coleccion.count_documents.assert_awaited_once_with(
        _construir_filtro(**{**_SIN_FILTROS, "visible_para": visible})
    )
