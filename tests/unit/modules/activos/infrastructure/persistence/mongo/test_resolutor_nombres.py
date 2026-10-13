from unittest.mock import AsyncMock, MagicMock, patch

from bson import ObjectId

from modules.activos.application.ports.resolutor_nombres import (
    CondicionResuelta,
    ReferenciasActivo,
)
from modules.activos.infrastructure.persistence.mongo.resolutor_nombres import (
    MongoResolutorNombres,
)

_MODULO = "modules.activos.infrastructure.persistence.mongo.resolutor_nombres"


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


async def test_resuelve_nombres_color_y_nombre_completo_del_responsable():
    cat, area, usr, cond, sede, lug = (ObjectId() for _ in range(6))
    base, _ = _base_con(
        {
            "categorias": [{"_id": cat, "nombre": "Computo"}],
            "areas": [{"_id": area, "nombre": "Tecnologia"}],
            "usuarios": [{"_id": usr, "nombre": "Ana", "apellido": "Gomez"}],
            "condiciones": [{"_id": cond, "nombre": "Bueno", "color": "#4CAF50"}],
            "sedes": [{"_id": sede, "nombre": "Prado"}],
            "lugares": [{"_id": lug, "nombre": "BANO1"}],
        }
    )
    referencias = ReferenciasActivo(
        categoria_ids={str(cat)},
        area_ids={str(area)},
        responsable_ids={str(usr)},
        condicion_ids={str(cond)},
        sede_ids={str(sede)},
        lugar_ids={str(lug)},
    )

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        nombres = await MongoResolutorNombres().resolver(referencias)

    assert nombres.categorias == {str(cat): "Computo"}
    assert nombres.areas == {str(area): "Tecnologia"}
    assert nombres.responsables == {str(usr): "Ana Gomez"}
    assert nombres.condiciones == {str(cond): CondicionResuelta(nombre="Bueno", color="#4CAF50")}
    assert nombres.sedes == {str(sede): "Prado"}
    assert nombres.lugares == {str(lug): "BANO1"}


async def test_consulta_cada_coleccion_con_in_de_object_ids_y_proyeccion_minima():
    usr = ObjectId()
    base, colecciones = _base_con({n: [] for n in ("categorias", "areas", "usuarios", "condiciones", "sedes", "lugares")})

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        await MongoResolutorNombres().resolver(ReferenciasActivo(responsable_ids={str(usr)}))

    filtro, proyeccion = colecciones["usuarios"].find.call_args.args
    assert filtro == {"_id": {"$in": [usr]}}
    assert proyeccion == {"nombre": 1, "apellido": 1}


async def test_no_consulta_colecciones_sin_ids_ni_con_ids_invalidos():
    base, colecciones = _base_con({n: [] for n in ("categorias", "areas", "usuarios", "condiciones", "sedes", "lugares")})

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        nombres = await MongoResolutorNombres().resolver(
            ReferenciasActivo(categoria_ids={"no-es-object-id"})
        )

    for coleccion in colecciones.values():
        coleccion.find.assert_not_called()
    assert nombres.categorias == {}


async def test_un_usuario_sin_apellido_usa_solo_el_nombre():
    usr = ObjectId()
    base, _ = _base_con(
        {
            "categorias": [],
            "areas": [],
            "usuarios": [{"_id": usr, "nombre": "Ana"}],
            "condiciones": [],
            "sedes": [],
            "lugares": [],
        }
    )

    with patch(f"{_MODULO}.mongo_manager") as manager:
        manager.get_database.return_value = base
        nombres = await MongoResolutorNombres().resolver(ReferenciasActivo(responsable_ids={str(usr)}))

    assert nombres.responsables == {str(usr): "Ana"}
