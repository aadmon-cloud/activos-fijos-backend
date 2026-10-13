from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from shared.application.user_auth.dto import EstadoUsuario
from shared.infrastructure.security.consulta_estado_usuario_mongo import (
    ConsultaEstadoUsuarioMongo,
)

_MODULO = "shared.infrastructure.security.consulta_estado_usuario_mongo"


def _coleccion_con(doc):
    coleccion = MagicMock()
    coleccion.find_one = AsyncMock(return_value=doc)
    base = MagicMock()
    base.__getitem__.return_value = coleccion

    return coleccion, base


async def test_devuelve_activo_y_rol_del_documento():
    id_usuario = str(ObjectId())
    coleccion, base = _coleccion_con({"_id": ObjectId(id_usuario), "activo": True, "rol": "tecnologia"})

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        estado = await ConsultaEstadoUsuarioMongo().obtener(id_usuario)

    assert estado == EstadoUsuario(activo=True, rol="tecnologia")
    filtro, proyeccion = coleccion.find_one.call_args.args
    assert filtro == {"_id": ObjectId(id_usuario)}
    assert proyeccion == {"activo": 1, "rol": 1, "area_id": 1}


async def test_devuelve_none_si_el_usuario_no_existe():
    _, base = _coleccion_con(None)

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        estado = await ConsultaEstadoUsuarioMongo().obtener(str(ObjectId()))

    assert estado is None


async def test_devuelve_none_sin_consultar_si_el_id_no_es_valido():
    with patch(f"{_MODULO}.mongo_manager") as manager:
        estado = await ConsultaEstadoUsuarioMongo().obtener("no-es-un-object-id")

    assert estado is None
    manager.get_database.assert_not_called()


async def test_un_documento_sin_campo_activo_se_trata_como_inactivo():
    _, base = _coleccion_con({"rol": "empleado"})

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        estado = await ConsultaEstadoUsuarioMongo().obtener(str(ObjectId()))

    assert estado == EstadoUsuario(activo=False, rol="empleado")


async def test_devuelve_el_area_del_usuario_como_texto():
    area = ObjectId()
    _, base = _coleccion_con({"activo": True, "rol": "empleado", "area_id": area})

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        estado = await ConsultaEstadoUsuarioMongo().obtener(str(ObjectId()))

    assert estado == EstadoUsuario(activo=True, rol="empleado", area_id=str(area))


async def test_un_usuario_sin_area_queda_con_area_none():
    _, base = _coleccion_con({"activo": True, "rol": "empleado", "area_id": None})

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        estado = await ConsultaEstadoUsuarioMongo().obtener(str(ObjectId()))

    assert estado.area_id is None
