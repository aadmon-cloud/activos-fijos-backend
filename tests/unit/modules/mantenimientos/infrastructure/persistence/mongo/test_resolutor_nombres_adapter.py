from unittest.mock import patch

from bson import ObjectId

from modules.mantenimientos.application.ports.resolutor_nombres_port import (
    ReferenciasMantenimiento,
)
from modules.mantenimientos.infrastructure.persistence.mongo.resolutor_nombres_adapter import (
    MongoResolutorNombresMantenimiento,
)

_RUTA = (
    "modules.mantenimientos.infrastructure.persistence.mongo.resolutor_nombres_adapter."
    "mongo_manager"
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

        resultado = await MongoResolutorNombresMantenimiento().resolver(
            ReferenciasMantenimiento(activo_ids=set(), tecnico_ids=set())
        )

    assert resultado.activos == {}
    assert resultado.tecnicos == {}


async def test_resolver_arma_los_diccionarios_de_activos_y_tecnicos():
    activo_id = ObjectId()
    tecnico_id = ObjectId()
    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = _db(
            activos=[{"_id": activo_id, "nombre": "Laptop", "numero_inventario": "INV-1"}],
            usuarios=[{"_id": tecnico_id, "nombre": "Ana", "apellido": "Perez"}],
        )

        resultado = await MongoResolutorNombresMantenimiento().resolver(
            ReferenciasMantenimiento(
                activo_ids={str(activo_id)}, tecnico_ids={str(tecnico_id)}
            )
        )

    assert resultado.activos[str(activo_id)].nombre == "Laptop"
    assert resultado.activos[str(activo_id)].numero_inventario == "INV-1"
    assert resultado.tecnicos[str(tecnico_id)] == "Ana Perez"
