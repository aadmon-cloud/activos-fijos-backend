from bson import ObjectId

from modules.mantenimientos.application.ports.solicitud_verificador_port import (
    SolicitudVerificadorPort,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Consulta la coleccion "solicitudes" por nombre en vez de importar modules.solicitudes: solo se
# necesita saber si existe y a que activo se refiere.
_NOMBRE_COLECCION_SOLICITUDES = "solicitudes"


class MongoSolicitudVerificador(SolicitudVerificadorPort):
    async def corresponde_al_activo(self, solicitud_id: str, activo_id: str) -> bool:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_SOLICITUDES]
        doc = await coleccion.find_one(
            {"_id": ObjectId(solicitud_id), "activo_id": ObjectId(activo_id)}, {"_id": 1}
        )

        return doc is not None
