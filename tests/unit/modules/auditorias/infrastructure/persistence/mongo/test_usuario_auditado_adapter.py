from unittest.mock import AsyncMock, patch

from bson import ObjectId

from modules.auditorias.infrastructure.persistence.mongo.usuario_auditado_adapter import (
    MongoUsuarioAuditadoAdapter,
)

_RUTA = "modules.auditorias.infrastructure.persistence.mongo.usuario_auditado_adapter.mongo_manager"


@patch(_RUTA)
async def test_obtener_retorna_none_si_no_existe(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = None
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    resultado = await MongoUsuarioAuditadoAdapter().obtener(str(ObjectId()))

    assert resultado is None


@patch(_RUTA)
async def test_obtener_arma_el_nombre_completo_y_los_datos_de_contacto(mongo_manager_mock):
    usuario_id = ObjectId()
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = {
        "_id": usuario_id,
        "nombre": "Camilo",
        "apellido": "Perez",
        "identificacion": "102425103",
        "email": "camilo@x.com",
        "activo": True,
    }
    mongo_manager_mock.get_database.return_value = {"usuarios": coleccion_mock}

    resultado = await MongoUsuarioAuditadoAdapter().obtener(str(usuario_id))

    assert resultado.id == str(usuario_id)
    assert resultado.nombre_completo == "Camilo Perez"
    assert resultado.identificacion == "102425103"
    assert resultado.email == "camilo@x.com"
    assert resultado.activo is True
