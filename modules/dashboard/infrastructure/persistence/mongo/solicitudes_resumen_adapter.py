from modules.dashboard.application.ports.solicitudes_resumen_port import SolicitudesResumenPort
from modules.dashboard.domain.entities import ResumenSolicitudes
from modules.dashboard.infrastructure.persistence.mongo.agregaciones import contar_y_agrupar
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "solicitudes"
_ESTADO_PENDIENTE = "pendiente"


class MongoSolicitudesResumenAdapter(SolicitudesResumenPort):
    async def obtener(self) -> ResumenSolicitudes:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
        total, agrupados = await contar_y_agrupar(coleccion, "estado", "tipo")
        por_estado = agrupados["estado"]

        return ResumenSolicitudes(
            total=total,
            por_estado=por_estado,
            por_tipo=agrupados["tipo"],
            pendientes=por_estado.get(_ESTADO_PENDIENTE, 0),
        )
