from modules.mantenimientos.infrastructure.api.dependencies import (
    get_verificar_alertas_mantenimiento_service,
)
from modules.movimientos.infrastructure.api.dependencies import (
    get_recordar_devoluciones_movimiento_service,
)
from modules.notificaciones.application.ports.tarea_recordatorio import TareaRecordatorioPort

# Unico archivo de notificaciones que usa servicios de otros modulos: el sistema de recordatorios solo
# necesita disparar lo que cada modulo ya sabe hacer (avisar de sus pendientes), sin duplicar esas reglas.


class AlertasMantenimientoTarea(TareaRecordatorioPort):
    async def ejecutar(self) -> int:
        return await get_verificar_alertas_mantenimiento_service().ejecutar()


class RecordatoriosDevolucionTarea(TareaRecordatorioPort):
    async def ejecutar(self) -> int:
        return await get_recordar_devoluciones_movimiento_service().ejecutar()
