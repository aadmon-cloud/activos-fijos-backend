from bson import ObjectId

from modules.mantenimientos.application.ports.resolutor_nombres_port import (
    ActivoNombre,
    NombresReferenciasMantenimiento,
    ReferenciasMantenimiento,
    ResolutorNombresMantenimientoPort,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION_ACTIVOS = "activos"
_NOMBRE_COLECCION_USUARIOS = "usuarios"


class MongoResolutorNombresMantenimiento(ResolutorNombresMantenimientoPort):
    async def resolver(
        self, referencias: ReferenciasMantenimiento
    ) -> NombresReferenciasMantenimiento:
        db = mongo_manager.get_database()

        activos: dict[str, ActivoNombre] = {}
        if referencias.activo_ids:
            ids = [ObjectId(i) for i in referencias.activo_ids]
            async for doc in db[_NOMBRE_COLECCION_ACTIVOS].find(
                {"_id": {"$in": ids}}, {"nombre": 1, "numero_inventario": 1}
            ):
                activos[str(doc["_id"])] = ActivoNombre(
                    nombre=doc["nombre"], numero_inventario=doc["numero_inventario"]
                )

        tecnicos: dict[str, str] = {}
        if referencias.tecnico_ids:
            ids = [ObjectId(i) for i in referencias.tecnico_ids]
            async for doc in db[_NOMBRE_COLECCION_USUARIOS].find(
                {"_id": {"$in": ids}}, {"nombre": 1, "apellido": 1}
            ):
                tecnicos[str(doc["_id"])] = f"{doc['nombre']} {doc['apellido']}".strip()

        return NombresReferenciasMantenimiento(activos=activos, tecnicos=tecnicos)
