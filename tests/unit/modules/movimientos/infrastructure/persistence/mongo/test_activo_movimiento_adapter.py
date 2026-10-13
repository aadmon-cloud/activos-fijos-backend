from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from modules.activos.domain.errors import ActivoNoEncontradoError, TransicionEstadoInvalidaError
from modules.movimientos.infrastructure.persistence.mongo.activo_movimiento_adapter import (
    MongoActivoMovimientoAdapter,
)

_RUTA_MONGO_MANAGER = (
    "modules.movimientos.infrastructure.persistence.mongo.activo_movimiento_adapter.mongo_manager"
)


@patch(_RUTA_MONGO_MANAGER)
async def test_obtener_resumen_retorna_none_si_no_existe(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = None
    mongo_manager_mock.get_database.return_value = {"activos": coleccion_mock}

    resultado = await MongoActivoMovimientoAdapter().obtener_resumen(str(ObjectId()))

    assert resultado is None


@patch(_RUTA_MONGO_MANAGER)
async def test_obtener_resumen_retorna_el_resumen_si_existe(mongo_manager_mock):
    activo_id = ObjectId()
    responsable_id = ObjectId()
    coleccion_mock = AsyncMock()
    coleccion_mock.find_one.return_value = {
        "_id": activo_id,
        "responsable_id": responsable_id,
        "estado_ciclo_vida": "disponible",
    }
    mongo_manager_mock.get_database.return_value = {"activos": coleccion_mock}

    resultado = await MongoActivoMovimientoAdapter().obtener_resumen(str(activo_id))

    assert resultado.id == str(activo_id)
    assert resultado.responsable_id == str(responsable_id)
    assert resultado.estado_ciclo_vida == "disponible"


async def test_cambiar_responsable_retorna_false_si_el_activo_no_existe():
    adapter = MongoActivoMovimientoAdapter()
    adapter._actualizar_activo = AsyncMock()
    adapter._actualizar_activo.ejecutar.side_effect = ActivoNoEncontradoError("a1")

    resultado = await adapter.cambiar_responsable("a1", "u2", "admin-1", "Admin")

    assert resultado is False


async def test_cambiar_responsable_retorna_true_si_tuvo_exito():
    adapter = MongoActivoMovimientoAdapter()
    adapter._actualizar_activo = AsyncMock()

    resultado = await adapter.cambiar_responsable("a1", "u2", "admin-1", "Admin")

    assert resultado is True
    adapter._actualizar_activo.ejecutar.assert_called_once()
    dto = adapter._actualizar_activo.ejecutar.call_args.args[0]
    assert dto.id_activo == "a1"
    assert dto.responsable_id == "u2"


async def test_cambiar_estado_retorna_false_si_la_transicion_es_invalida():
    adapter = MongoActivoMovimientoAdapter()
    adapter._cambiar_estado_activo = AsyncMock()
    adapter._cambiar_estado_activo.ejecutar.side_effect = TransicionEstadoInvalidaError(
        "prestado", "dado_de_baja"
    )

    resultado = await adapter.cambiar_estado("a1", "dado_de_baja", "admin-1", "Admin")

    assert resultado is False


async def test_cambiar_estado_retorna_true_si_tuvo_exito():
    adapter = MongoActivoMovimientoAdapter()
    adapter._cambiar_estado_activo = AsyncMock()

    resultado = await adapter.cambiar_estado("a1", "prestado", "admin-1", "Admin")

    assert resultado is True
    dto = adapter._cambiar_estado_activo.ejecutar.call_args.args[0]
    assert dto.id_activo == "a1"
    assert dto.estado_nuevo.value == "prestado"


@patch(_RUTA_MONGO_MANAGER)
async def test_listar_ids_por_responsable_consulta_por_object_id_y_devuelve_textos(mongo_manager_mock):
    responsable_id = ObjectId()
    activo_a, activo_b = ObjectId(), ObjectId()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(return_value=[{"_id": activo_a}, {"_id": activo_b}])
    coleccion_mock = MagicMock()
    coleccion_mock.find = MagicMock(return_value=cursor)
    mongo_manager_mock.get_database.return_value = {"activos": coleccion_mock}

    ids = await MongoActivoMovimientoAdapter().listar_ids_por_responsable(str(responsable_id))

    assert ids == [str(activo_a), str(activo_b)]
    filtro, proyeccion = coleccion_mock.find.call_args.args
    assert filtro == {"responsable_id": responsable_id}
    assert proyeccion == {"_id": 1}


@patch(_RUTA_MONGO_MANAGER)
async def test_obtener_resumenes_devuelve_un_resumen_por_cada_activo_que_existe(mongo_manager_mock):
    activo_a, activo_b, inexistente = ObjectId(), ObjectId(), ObjectId()
    responsable = ObjectId()
    cursor = MagicMock()
    cursor.to_list = AsyncMock(
        return_value=[
            {"_id": activo_a, "responsable_id": responsable, "estado_ciclo_vida": "disponible", "nombre": "Laptop"},
            {"_id": activo_b, "responsable_id": responsable, "estado_ciclo_vida": "prestado"},
        ]
    )
    coleccion_mock = MagicMock()
    coleccion_mock.find = MagicMock(return_value=cursor)
    mongo_manager_mock.get_database.return_value = {"activos": coleccion_mock}

    resumenes = await MongoActivoMovimientoAdapter().obtener_resumenes(
        [str(activo_a), str(activo_b), str(inexistente)]
    )

    assert set(resumenes) == {str(activo_a), str(activo_b)}
    assert resumenes[str(activo_a)].nombre == "Laptop"
    assert resumenes[str(activo_b)].estado_ciclo_vida == "prestado"
    filtro = coleccion_mock.find.call_args.args[0]
    assert set(filtro["_id"]["$in"]) == {activo_a, activo_b, inexistente}


@patch(_RUTA_MONGO_MANAGER)
async def test_obtener_resumenes_sin_ids_no_consulta(mongo_manager_mock):
    assert await MongoActivoMovimientoAdapter().obtener_resumenes([]) == {}

    mongo_manager_mock.get_database.assert_not_called()


@patch(_RUTA_MONGO_MANAGER)
async def test_registrar_nota_escribe_una_entrada_de_tipo_nota_en_el_historial_del_activo(mongo_manager_mock):
    coleccion_mock = AsyncMock()
    mongo_manager_mock.get_database.return_value = {"activos_historial": coleccion_mock}
    activo_id, movimiento_id = ObjectId(), ObjectId()

    await MongoActivoMovimientoAdapter().registrar_nota(
        str(activo_id), "Pantalla rayada", str(movimiento_id), "admin-1", "Admin"
    )

    documento = coleccion_mock.insert_one.await_args.args[0]
    assert documento["activo_id"] == activo_id
    assert documento["tipo"] == "nota"
    assert documento["nota"] == "Pantalla rayada"
    assert documento["movimiento_id"] == movimiento_id
    assert documento["modificado_por"]["id_persona"] == "admin-1"
    assert documento["modificado_por"]["nombre"] == "Admin"
    assert documento["modificado_por"]["fecha"] is not None

