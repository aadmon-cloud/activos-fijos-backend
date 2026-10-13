from bson import ObjectId
from bson.errors import InvalidId

from shared.application.user_auth.dto import EstadoUsuario
from shared.application.user_auth.ports import ConsultaEstadoUsuarioPort
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Consulta la coleccion "usuarios" por nombre en vez de importar modules.usuarios: shared no
# puede depender de un modulo, al costo de conocer el nombre de la coleccion.
_NOMBRE_COLECCION_USUARIOS = "usuarios"


class ConsultaEstadoUsuarioMongo(ConsultaEstadoUsuarioPort):
    async def obtener(self, id_usuario: str) -> EstadoUsuario | None:
        try:
            id_documento = ObjectId(id_usuario)
        except (InvalidId, TypeError):
            return None

        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_USUARIOS]
        doc = await coleccion.find_one({"_id": id_documento}, {"activo": 1, "rol": 1, "area_id": 1})
        if doc is None:
            return None

        area = doc.get("area_id")

        return EstadoUsuario(
            activo=bool(doc.get("activo", False)),
            rol=doc.get("rol", ""),
            area_id=str(area) if area else None,
        )
