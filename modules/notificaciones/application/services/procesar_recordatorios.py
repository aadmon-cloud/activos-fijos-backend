import logging

from modules.notificaciones.application.dto.notificacion_dto import ResultadoRecordatoriosDTO
from modules.notificaciones.application.ports.tarea_recordatorio import TareaRecordatorioPort

logger = logging.getLogger(__name__)


class ProcesarRecordatoriosService:
    """Ejecuta las tareas diarias de aviso: proximos mantenimientos y devoluciones. Cada una es
    independiente: si una falla, la otra se ejecuta igual y el error queda en el resultado."""

    def __init__(
        self,
        alertas_mantenimiento: TareaRecordatorioPort,
        recordatorios_devolucion: TareaRecordatorioPort,
    ):
        self._alertas_mantenimiento = alertas_mantenimiento
        self._recordatorios_devolucion = recordatorios_devolucion

    async def ejecutar(self) -> ResultadoRecordatoriosDTO:
        errores: list[str] = []
        mantenimientos = await self._correr("mantenimientos", self._alertas_mantenimiento, errores)
        devoluciones = await self._correr("devoluciones", self._recordatorios_devolucion, errores)

        return ResultadoRecordatoriosDTO(
            mantenimientos_avisados=mantenimientos,
            devoluciones_recordadas=devoluciones,
            errores=errores,
        )

    @staticmethod
    async def _correr(nombre: str, tarea: TareaRecordatorioPort, errores: list[str]) -> int | None:
        try:
            return await tarea.ejecutar()
        except Exception as exc:
            logger.exception("Fallo la tarea de recordatorios '%s'", nombre)
            errores.append(f"{nombre}: {type(exc).__name__}")

            return None
