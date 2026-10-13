from modules.dashboard.application.ports.movimientos_resumen_port import MovimientosResumenPort
from modules.dashboard.domain.entities import ResumenMovimientos
from modules.dashboard.infrastructure.persistence.mongo.agregaciones import contar_y_agrupar
from shared.infrastructure.persistence.mongo.database import mongo_manager

_NOMBRE_COLECCION = "movimientos"
# Esperando una decision de aprobar/rechazar -- 'aprobado' ya fue decidido y espera confirmar-
# salida/ejecutar-baja, 'en_curso' espera devolucion: ninguno de esos dos es "pendiente de aprobar".
_ESTADOS_PENDIENTES_DE_APROBACION = ("solicitado", "aprobado_responsable")


class MongoMovimientosResumenAdapter(MovimientosResumenPort):
    async def obtener(self) -> ResumenMovimientos:
        coleccion = mongo_manager.get_database()[_NOMBRE_COLECCION]
        total, agrupados = await contar_y_agrupar(coleccion, "tipo", "estado")
        por_estado = agrupados["estado"]

        pendientes_de_aprobacion = sum(
            por_estado.get(estado, 0) for estado in _ESTADOS_PENDIENTES_DE_APROBACION
        )

        return ResumenMovimientos(
            total=total,
            por_tipo=agrupados["tipo"],
            por_estado=por_estado,
            pendientes_de_aprobacion=pendientes_de_aprobacion,
        )
