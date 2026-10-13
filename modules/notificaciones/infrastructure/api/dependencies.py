from modules.notificaciones.application.services.listar_notificaciones import (
    ListarNotificacionesService,
)
from modules.notificaciones.application.services.procesar_recordatorios import (
    ProcesarRecordatoriosService,
)
from modules.notificaciones.application.services.reenviar_notificacion import (
    ReenviarNotificacionService,
)
from modules.notificaciones.infrastructure.adapters.tareas_recordatorio import (
    AlertasMantenimientoTarea,
    RecordatoriosDevolucionTarea,
)
from modules.notificaciones.infrastructure.composicion import (
    get_configuracion_correo,
    get_correo,
    get_notificacion_repository,
    get_resolutor_destinatarios,
)

__all__ = ["get_configuracion_correo"]


def get_listar_notificaciones_service() -> ListarNotificacionesService:
    return ListarNotificacionesService(notificacion_repository=get_notificacion_repository())


def get_reenviar_notificacion_service() -> ReenviarNotificacionService:
    return ReenviarNotificacionService(
        notificacion_repository=get_notificacion_repository(),
        resolutor=get_resolutor_destinatarios(),
        configuracion=get_configuracion_correo(),
        correo=get_correo(),
    )


def get_procesar_recordatorios_service() -> ProcesarRecordatoriosService:
    return ProcesarRecordatoriosService(
        alertas_mantenimiento=AlertasMantenimientoTarea(),
        recordatorios_devolucion=RecordatoriosDevolucionTarea(),
    )
