from bson import ObjectId

from modules.auditorias.application.ports.activos_asignados_port import (
    ActivoAsignado,
    ActivosAsignadosPort,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

# Consulta la coleccion "activos" por nombre en vez de importar modules.activos: evita que
# auditorias dependa del codigo de otro modulo.
_NOMBRE_COLECCION_ACTIVOS = "activos"

# Solo se audita lo que hoy representa una asignacion fisica activa: un activo dado de baja,
# perdido o danado ya no es responsabilidad fisica real del usuario, aunque el campo
# responsable_id quede como dato historico.
_ESTADOS_ASIGNACION_ACTIVA = ("disponible", "prestado", "en_mantenimiento")


class MongoActivosAsignadosAdapter(ActivosAsignadosPort):
    async def listar_por_responsable(self, usuario_id: str) -> list[ActivoAsignado]:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION_ACTIVOS]
        cursor = coleccion.find(
            {
                "responsable_id": ObjectId(usuario_id),
                "estado_ciclo_vida": {"$in": _ESTADOS_ASIGNACION_ACTIVA},
            }
        )
        return [
            ActivoAsignado(
                id=str(doc["_id"]),
                nombre=doc["nombre"],
                numero_inventario=doc["numero_inventario"],
                tipo=doc["tipo"],
                descripcion=doc.get("descripcion"),
                serie=doc.get("serie"),
                estado_ciclo_vida=doc["estado_ciclo_vida"],
            )
            async for doc in cursor
        ]
