from bson import ObjectId

from modules.auditorias.application.ports.usuario_auditado_port import (
    UsuarioAuditado,
    UsuarioAuditadoPort,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION_USUARIOS = "usuarios"


class MongoUsuarioAuditadoAdapter(UsuarioAuditadoPort):
    async def obtener(self, usuario_id: str) -> UsuarioAuditado | None:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_USUARIOS]
        doc = await coleccion.find_one({"_id": ObjectId(usuario_id)})
        if doc is None:
            return None
        return UsuarioAuditado(
            id=str(doc["_id"]),
            nombre_completo=f"{doc['nombre']} {doc['apellido']}".strip(),
            identificacion=doc.get("identificacion"),
            email=doc["email"],
            activo=doc.get("activo", True),
        )
