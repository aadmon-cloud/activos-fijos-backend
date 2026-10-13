from dataclasses import replace
from datetime import UTC, datetime, timedelta

from modules.mantenimientos.application.ports.activo_resumen_port import ActivoResumenPort
from modules.mantenimientos.application.ports.mantenimiento_repository import (
    MantenimientoRepositoryPort,
)
from shared.application.notifications.enlaces import enlace
from shared.application.notifications.ports import NotificadorPort

_VENTANA_DIAS_DEFECTO = 7
_ROL_MANTENIMIENTO = "mantenimiento"


class VerificarAlertasMantenimientoService:
    def __init__(
        self,
        mantenimiento_repository: MantenimientoRepositoryPort,
        activo_resumen_port: ActivoResumenPort,
        notificador: NotificadorPort,
    ):
        self._mantenimiento_repository = mantenimiento_repository
        self._activo_resumen_port = activo_resumen_port
        self._notificador = notificador

    async def ejecutar(self, ventana_dias: int = _VENTANA_DIAS_DEFECTO) -> int:
        limite = datetime.now(UTC) + timedelta(days=ventana_dias)
        pendientes = await self._mantenimiento_repository.listar_pendientes_de_alerta(limite)

        for mantenimiento in pendientes:
            activo = await self._activo_resumen_port.obtener_resumen(mantenimiento.activo_id)
            # Responsable del activo, area correspondiente y area de mantenimiento.
            destinatarios = [f"rol:{_ROL_MANTENIMIENTO}"]
            if activo is not None:
                destinatarios += [f"usuario:{activo.responsable_id}", f"area:{activo.area_id}"]

            nombre = (
                f"{activo.nombre} ({activo.numero_inventario})"
                if activo is not None and activo.nombre
                else "un activo"
            )
            await self._notificador.notificar(
                destinatarios=destinatarios,
                asunto=f"Proximo mantenimiento: {nombre}",
                cuerpo=(
                    f"{nombre} tiene un mantenimiento sugerido para el "
                    f"{mantenimiento.proxima_fecha_sugerida.strftime('%d/%m/%Y')}.\n\n"
                    f"Ver el mantenimiento anterior: "
                    f"{enlace(f'/mantenimientos/detalle?id={mantenimiento.id}')}"
                ),
            )

            await self._mantenimiento_repository.guardar(
                replace(mantenimiento, alerta_enviada=True)
            )

        return len(pendientes)
