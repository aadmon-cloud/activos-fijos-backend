from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from modules.solicitudes.application.ports.solicitud_repository import VisibilidadSolicitud
from modules.solicitudes.domain.entities import EstadoSolicitud, TipoSolicitud
from modules.solicitudes.infrastructure.persistence.mongo.solicitud_repository import (
    MongoSolicitudRepository,
    _construir_filtro,
)

_MODULO = "modules.solicitudes.infrastructure.persistence.mongo.solicitud_repository"

_SIN_FILTROS = dict(
    tipo=None,
    estado=None,
    activo_id=None,
    rol_asignado=None,
    area_id=None,
    creado_por_id=None,
    visible_para=None,
)


def test_sin_filtros_el_filtro_esta_vacio():
    assert _construir_filtro(**_SIN_FILTROS) == {}


def test_los_filtros_se_convierten_a_su_representacion_en_mongo():
    activo = str(ObjectId())

    filtro = _construir_filtro(
        **{
            **_SIN_FILTROS,
            "tipo": TipoSolicitud.CAMBIO,
            "estado": EstadoSolicitud.PENDIENTE,
            "activo_id": activo,
            "creado_por_id": "u1",
        }
    )

    assert filtro == {
        "tipo": "cambio",
        "estado": "pendiente",
        "activo_id": ObjectId(activo),
        "creado_por.id_persona": "u1",
    }


def test_la_visibilidad_limita_a_lo_creado_o_asignado_al_rol_o_al_area():
    area = str(ObjectId())

    filtro = _construir_filtro(
        **{**_SIN_FILTROS, "visible_para": VisibilidadSolicitud("u1", "tecnologia", area)}
    )

    assert filtro == {
        "$or": [
            {"creado_por.id_persona": "u1"},
            {"rol_asignado": "tecnologia"},
            {"area_id": ObjectId(area)},
        ]
    }


def test_sin_area_la_visibilidad_no_incluye_la_condicion_de_area():
    filtro = _construir_filtro(
        **{**_SIN_FILTROS, "visible_para": VisibilidadSolicitud("u1", "empleado", None)}
    )

    assert filtro["$or"] == [
        {"creado_por.id_persona": "u1"},
        {"rol_asignado": "empleado"},
    ]


def test_la_visibilidad_se_combina_con_los_demas_filtros_sin_reemplazarlos():
    filtro = _construir_filtro(
        **{
            **_SIN_FILTROS,
            "estado": EstadoSolicitud.PENDIENTE,
            "visible_para": VisibilidadSolicitud("u1", "empleado", None),
        }
    )

    assert filtro["estado"] == "pendiente"
    assert "$or" in filtro


@patch(f"{_MODULO}.mongo_manager")
async def test_contar_usa_el_mismo_filtro_que_listar(mongo_manager_mock):
    coleccion = MagicMock()
    coleccion.count_documents = AsyncMock(return_value=7)
    mongo_manager_mock.get_database.return_value = {"solicitudes": coleccion}
    visible = VisibilidadSolicitud("u1", "empleado", None)

    total = await MongoSolicitudRepository().contar(**{**_SIN_FILTROS, "visible_para": visible})

    assert total == 7
    coleccion.count_documents.assert_awaited_once_with(
        _construir_filtro(**{**_SIN_FILTROS, "visible_para": visible})
    )
