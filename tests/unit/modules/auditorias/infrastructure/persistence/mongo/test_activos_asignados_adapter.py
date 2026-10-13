from unittest.mock import patch

from bson import ObjectId

from modules.auditorias.infrastructure.persistence.mongo.activos_asignados_adapter import (
    MongoActivosAsignadosAdapter,
)

_RUTA = (
    "modules.auditorias.infrastructure.persistence.mongo.activos_asignados_adapter.mongo_manager"
)


class _Cursor:
    def __init__(self, documentos):
        self._documentos = documentos

    def __aiter__(self):
        return self._generador()

    async def _generador(self):
        for doc in self._documentos:
            yield doc


class _Coleccion:
    def __init__(self, documentos):
        self._documentos = documentos
        self.filtro_usado = None

    def find(self, filtro):
        self.filtro_usado = filtro
        return _Cursor(self._documentos)


async def test_listar_por_responsable_filtra_por_responsable_y_estado_de_asignacion_activa():
    usuario_id = str(ObjectId())
    activo_id = ObjectId()
    coleccion = _Coleccion(
        [
            {
                "_id": activo_id,
                "nombre": "Laptop",
                "numero_inventario": "INV-1",
                "tipo": "activo_fijo",
                "descripcion": "Dell",
                "serie": "SN1",
                "estado_ciclo_vida": "disponible",
            }
        ]
    )

    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = {"activos": coleccion}
        resultado = await MongoActivosAsignadosAdapter().listar_por_responsable(usuario_id)

    assert coleccion.filtro_usado["responsable_id"] == ObjectId(usuario_id)
    assert set(coleccion.filtro_usado["estado_ciclo_vida"]["$in"]) == {
        "disponible",
        "prestado",
        "en_mantenimiento",
    }
    assert len(resultado) == 1
    assert resultado[0].id == str(activo_id)
    assert resultado[0].numero_inventario == "INV-1"
    assert resultado[0].descripcion == "Dell"


async def test_listar_por_responsable_retorna_vacio_sin_activos():
    with patch(_RUTA) as mongo_manager_mock:
        mongo_manager_mock.get_database.return_value = {"activos": _Coleccion([])}
        resultado = await MongoActivosAsignadosAdapter().listar_por_responsable(str(ObjectId()))

    assert resultado == []
