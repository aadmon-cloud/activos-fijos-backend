from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from modules.solicitudes.application.ports.resolutor_referencias import (
    ActivoNombre,
    ReferenciasSolicitud,
)
from modules.solicitudes.infrastructure.persistence.mongo.resolutor_referencias import (
    MongoResolutorReferencias,
)

_MODULO = "modules.solicitudes.infrastructure.persistence.mongo.resolutor_referencias"


def _base_con(docs_por_coleccion: dict[str, list[dict]]):
    colecciones = {}
    for nombre, docs in docs_por_coleccion.items():
        cursor = MagicMock()
        cursor.to_list = AsyncMock(return_value=docs)
        coleccion = MagicMock()
        coleccion.find = MagicMock(return_value=cursor)
        colecciones[nombre] = coleccion

    base = MagicMock()
    base.__getitem__.side_effect = lambda nombre: colecciones[nombre]

    return base, colecciones


async def test_resuelve_nombre_e_inventario_del_activo_y_nombre_del_area():
    activo, area = ObjectId(), ObjectId()
    base, _ = _base_con(
        {
            "activos": [{"_id": activo, "nombre": "Laptop", "numero_inventario": "INV-1"}],
            "areas": [{"_id": area, "nombre": "Tecnologia"}],
        }
    )

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        nombres = await MongoResolutorReferencias().resolver(
            ReferenciasSolicitud(activo_ids={str(activo)}, area_ids={str(area)})
        )

    assert nombres.activos == {str(activo): ActivoNombre("Laptop", "INV-1")}
    assert nombres.areas == {str(area): "Tecnologia"}


async def test_consulta_con_in_de_object_ids_y_proyeccion_minima():
    activo = ObjectId()
    base, colecciones = _base_con({"activos": [], "areas": []})

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        await MongoResolutorReferencias().resolver(ReferenciasSolicitud(activo_ids={str(activo)}))

    filtro, proyeccion = colecciones["activos"].find.call_args.args
    assert filtro == {"_id": {"$in": [activo]}}
    assert proyeccion == {"nombre": 1, "numero_inventario": 1}
    colecciones["areas"].find.assert_not_called()


async def test_ignora_ids_invalidos_sin_consultar():
    base, colecciones = _base_con({"activos": [], "areas": []})

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        nombres = await MongoResolutorReferencias().resolver(
            ReferenciasSolicitud(activo_ids={"no-es-object-id"})
        )

    for coleccion in colecciones.values():
        coleccion.find.assert_not_called()
    assert nombres.activos == {}


async def test_un_activo_sin_numero_de_inventario_queda_con_cadena_vacia():
    activo = ObjectId()
    base, _ = _base_con({"activos": [{"_id": activo, "nombre": "Mesa"}], "areas": []})

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        nombres = await MongoResolutorReferencias().resolver(
            ReferenciasSolicitud(activo_ids={str(activo)})
        )

    assert nombres.activos[str(activo)].numero_inventario == ""
