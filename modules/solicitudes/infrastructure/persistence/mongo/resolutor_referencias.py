import asyncio

from bson import ObjectId
from bson.errors import InvalidId

from modules.solicitudes.application.ports.resolutor_referencias import (
    ActivoNombre,
    NombresReferenciasSolicitud,
    ReferenciasSolicitud,
    ResolutorReferenciasPort,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Consulta las colecciones "activos" y "areas" por nombre en vez de importar sus modulos:
# solicitudes no depende del codigo de otro modulo, al costo de conocer los nombres de coleccion.
_COLECCION_ACTIVOS = "activos"
_COLECCION_AREAS = "areas"


def _a_object_ids(ids: set[str]) -> list[ObjectId]:
    validos = []
    for id_ in ids:
        try:
            validos.append(ObjectId(id_))
        except (InvalidId, TypeError):
            continue

    return validos


class MongoResolutorReferencias(ResolutorReferenciasPort):
    async def _documentos(self, coleccion: str, ids: set[str], proyeccion: dict) -> list[dict]:
        object_ids = _a_object_ids(ids)
        if not object_ids:
            return []

        cursor = mongo_manager.get_database()[coleccion].find(
            {"_id": {"$in": object_ids}}, proyeccion
        )
        return await cursor.to_list(length=None)

    async def resolver(self, referencias: ReferenciasSolicitud) -> NombresReferenciasSolicitud:
        activos, areas = await asyncio.gather(
            self._documentos(
                _COLECCION_ACTIVOS, referencias.activo_ids, {"nombre": 1, "numero_inventario": 1}
            ),
            self._documentos(_COLECCION_AREAS, referencias.area_ids, {"nombre": 1}),
        )

        return NombresReferenciasSolicitud(
            activos={
                str(d["_id"]): ActivoNombre(
                    nombre=d["nombre"], numero_inventario=d.get("numero_inventario", "")
                )
                for d in activos
            },
            areas={str(d["_id"]): d["nombre"] for d in areas},
        )
