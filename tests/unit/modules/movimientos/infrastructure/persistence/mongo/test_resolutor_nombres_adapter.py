from unittest.mock import patch

from bson import ObjectId

from modules.movimientos.application.ports.resolutor_nombres_port import ReferenciasMovimiento
from modules.movimientos.infrastructure.persistence.mongo.resolutor_nombres_adapter import (
    MongoResolutorNombresMovimiento,
)

_RUTA = (
    "modules.movimientos.infrastructure.persistence.mongo.resolutor_nombres_adapter.mongo_manager"
)


class _Cursor:
    def __init__(self, documentos):
        self._documentos = documentos

    def __aiter__(self):
        return self._generador()

    async def _generador(self):
        for doc in self._documentos:
            yield doc


def _db(activos=None, usuarios=None):
    coleccion_activos = type("C", (), {"find": lambda self, *a, **k: _Cursor(activos or [])})()
    coleccion_usuarios = type("C", (), {"find": lambda self, *a, **k: _Cursor(usuarios or [])})()
    return {"activos": coleccion_activos, "usuarios": coleccion_usuarios}


async def test_resolver_retorna_vacio_si_no_hay_referencias():
    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = _db()

        resultado = await MongoResolutorNombresMovimiento().resolver(ReferenciasMovimiento())

    assert resultado.activos == {}
    assert resultado.usuarios == {}


async def test_resolver_arma_los_diccionarios_de_activos_y_usuarios():
    activo_id = ObjectId()
    usuario_id = ObjectId()
    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = _db(
            activos=[{"_id": activo_id, "nombre": "Laptop", "numero_inventario": "INV-1"}],
            usuarios=[{"_id": usuario_id, "nombre": "Ana", "apellido": "Perez"}],
        )

        resultado = await MongoResolutorNombresMovimiento().resolver(
            ReferenciasMovimiento(activo_ids={str(activo_id)}, usuario_ids={str(usuario_id)})
        )

    assert resultado.activos[str(activo_id)].nombre == "Laptop"
    assert resultado.activos[str(activo_id)].numero_inventario == "INV-1"
    assert resultado.usuarios[str(usuario_id)] == "Ana Perez"


async def test_resolver_devuelve_el_responsable_actual_del_activo():
    activo_id, responsable_id = ObjectId(), ObjectId()
    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = _db(
            activos=[
                {
                    "_id": activo_id,
                    "nombre": "Laptop",
                    "numero_inventario": "INV-1",
                    "responsable_id": responsable_id,
                }
            ]
        )

        resultado = await MongoResolutorNombresMovimiento().resolver(
            ReferenciasMovimiento(activo_ids={str(activo_id)})
        )

    assert resultado.activos[str(activo_id)].responsable_id == str(responsable_id)
    assert resultado.responsables_actuales() == {str(activo_id): str(responsable_id)}


async def test_resolver_consulta_los_usuarios_en_una_sola_consulta():
    uno, dos = ObjectId(), ObjectId()
    consultas = []

    class _Coleccion:
        def find(self, filtro, proyeccion):
            consultas.append(filtro)

            return _Cursor(
                [
                    {"_id": uno, "nombre": "Ana", "apellido": "Perez"},
                    {"_id": dos, "nombre": "Luis", "apellido": "Gomez"},
                ]
            )

    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = {"activos": _Coleccion(), "usuarios": _Coleccion()}

        resultado = await MongoResolutorNombresMovimiento().resolver(
            ReferenciasMovimiento(usuario_ids={str(uno), str(dos)})
        )

    assert len(consultas) == 1
    assert resultado.usuarios == {str(uno): "Ana Perez", str(dos): "Luis Gomez"}
