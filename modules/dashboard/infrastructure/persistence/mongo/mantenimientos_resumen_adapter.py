from datetime import UTC, datetime, timedelta

from modules.dashboard.application.ports.mantenimientos_resumen_port import (
    MantenimientosResumenPort,
)
from modules.dashboard.domain.entities import ResumenMantenimientos
from modules.dashboard.infrastructure.persistence.mongo.agregaciones import contar_y_agrupar
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "mantenimientos"
_ESTADO_COMPLETADO = "completado"
# Misma ventana que modules.mantenimientos.application.services.verificar_alertas_mantenimiento.
_VENTANA_DIAS_ALERTA = 7


class MongoMantenimientosResumenAdapter(MantenimientosResumenPort):
    async def obtener(self) -> ResumenMantenimientos:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
        total, agrupados = await contar_y_agrupar(coleccion, "estado")

        limite_fecha = datetime.now(UTC) + timedelta(days=_VENTANA_DIAS_ALERTA)
        pendientes_de_alerta = await coleccion.count_documents(
            {
                "estado": _ESTADO_COMPLETADO,
                "alerta_enviada": False,
                "proxima_fecha_sugerida": {"$ne": None, "$lte": limite_fecha},
            }
        )

        return ResumenMantenimientos(
            total=total,
            por_estado=agrupados["estado"],
            pendientes_de_alerta=pendientes_de_alerta,
        )
