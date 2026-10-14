from bson import ObjectId

from modules.movimientos.application.ports.resolutor_nombres_port import (
    ActivoNombreMovimiento,
    NombresReferenciasMovimiento,
    ReferenciasMovimiento,
    ResolutorNombresMovimientoPort,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION_ACTIVOS = "activos"
_NOMBRE_COLECCION_USUARIOS = "usuarios"


class MongoResolutorNombresMovimiento(ResolutorNombresMovimientoPort):
    async def resolver(
        self, referencias: ReferenciasMovimiento
    ) -> NombresReferenciasMovimiento:
        db = mongo_manager.get_database()

        activos: dict[str, ActivoNombreMovimiento] = {}
        if referencias.activo_ids:
            ids = [ObjectId(i) for i in referencias.activo_ids]
            async for doc in db[_NOMBRE_COLECCION_ACTIVOS].find(
                {"_id": {"$in": ids}}, {"nombre": 1, "numero_inventario": 1, "responsable_id": 1}
            ):
                activos[str(doc["_id"])] = ActivoNombreMovimiento(
                    nombre=doc["nombre"],
                    numero_inventario=doc["numero_inventario"],
                    responsable_id=str(doc["responsable_id"]) if doc.get("responsable_id") else None,
                )

        usuarios: dict[str, str] = {}
        correos: dict[str, str] = {}
        if referencias.usuario_ids:
            ids = [ObjectId(i) for i in referencias.usuario_ids]
            async for doc in db[_NOMBRE_COLECCION_USUARIOS].find(
                {"_id": {"$in": ids}}, {"nombre": 1, "apellido": 1, "email": 1}
            ):
                usuarios[str(doc["_id"])] = f"{doc['nombre']} {doc['apellido']}".strip()
                correos[str(doc["_id"])] = doc.get("email", "")

        return NombresReferenciasMovimiento(activos=activos, usuarios=usuarios, correos=correos)
