from bson import ObjectId

from modules.movimientos.application.ports.verificador_usuario_port import VerificadorUsuarioPort
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION_USUARIOS = "usuarios"


class MongoVerificadorUsuario(VerificadorUsuarioPort):
    async def existe(self, usuario_id: str) -> bool:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_USUARIOS]
        doc = await coleccion.find_one({"_id": ObjectId(usuario_id)})
        return doc is not None
