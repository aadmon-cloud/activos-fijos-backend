import asyncio

from bson import ObjectId
from bson.errors import InvalidId

from modules.activos.application.ports.resolutor_nombres import (
    CondicionResuelta,
    NombresReferencias,
    ReferenciasActivo,
    ResolutorNombresPort,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Consulta las colecciones de catalogos y usuarios por nombre en vez de importar sus modulos:
# activos no depende del codigo de otro modulo, al costo de conocer los nombres de coleccion.
_COLECCION_CATEGORIAS = "categorias"
_COLECCION_AREAS = "areas"
_COLECCION_USUARIOS = "usuarios"
_COLECCION_CONDICIONES = "condiciones"
_COLECCION_SEDES = "sedes"
_COLECCION_LUGARES = "lugares"


def _a_object_ids(ids: set[str]) -> list[ObjectId]:
    validos = []
    for id_ in ids:
        try:
            validos.append(ObjectId(id_))
        except (InvalidId, TypeError):
            continue

    return validos


class MongoResolutorNombres(ResolutorNombresPort):
    async def _documentos(self, coleccion: str, ids: set[str], proyeccion: dict) -> list[dict]:
        object_ids = _a_object_ids(ids)
        if not object_ids:
            return []

        cursor = mongo_manager.get_database()[coleccion].find(
            {"_id": {"$in": object_ids}}, proyeccion
        )
        return await cursor.to_list(length=None)

    async def resolver(self, referencias: ReferenciasActivo) -> NombresReferencias:
        nombre = {"nombre": 1}
        categorias, areas, usuarios, condiciones, sedes, lugares = await asyncio.gather(
            self._documentos(_COLECCION_CATEGORIAS, referencias.categoria_ids, nombre),
            self._documentos(_COLECCION_AREAS, referencias.area_ids, nombre),
            self._documentos(
                _COLECCION_USUARIOS, referencias.responsable_ids, {"nombre": 1, "apellido": 1}
            ),
            self._documentos(
                _COLECCION_CONDICIONES, referencias.condicion_ids, {"nombre": 1, "color": 1}
            ),
            self._documentos(_COLECCION_SEDES, referencias.sede_ids, nombre),
            self._documentos(_COLECCION_LUGARES, referencias.lugar_ids, nombre),
        )

        return NombresReferencias(
            categorias={str(d["_id"]): d["nombre"] for d in categorias},
            areas={str(d["_id"]): d["nombre"] for d in areas},
            responsables={
                str(d["_id"]): f"{d['nombre']} {d.get('apellido', '')}".strip() for d in usuarios
            },
            condiciones={
                str(d["_id"]): CondicionResuelta(nombre=d["nombre"], color=d.get("color", ""))
                for d in condiciones
            },
            sedes={str(d["_id"]): d["nombre"] for d in sedes},
            lugares={str(d["_id"]): d["nombre"] for d in lugares},
        )
