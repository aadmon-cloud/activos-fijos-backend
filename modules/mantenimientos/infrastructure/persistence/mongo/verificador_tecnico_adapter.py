from bson import ObjectId

from modules.mantenimientos.application.ports.verificador_tecnico_port import (
    VerificadorTecnicoPort,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION_USUARIOS = "usuarios"
_ROL_MANTENIMIENTO = "mantenimiento"


class MongoVerificadorTecnico(VerificadorTecnicoPort):
    async def tiene_rol_mantenimiento(self, usuario_id: str) -> bool:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_USUARIOS]
        doc = await coleccion.find_one({"_id": ObjectId(usuario_id)})
        # Un tecnico desactivado no puede recibir mantenimientos.
        return doc is not None and doc.get("rol") == _ROL_MANTENIMIENTO and bool(doc.get("activo"))
