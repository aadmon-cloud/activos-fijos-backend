from modules.mantenimientos.application.ports.solicitud_estado_port import (
    ActorSolicitud,
    SolicitudEstadoPort,
)
from modules.solicitudes.application.dto.cambiar_estado_solicitud_dto import (
    CambiarEstadoSolicitudDTO,
)
from modules.solicitudes.domain.entities import EstadoSolicitud
from modules.solicitudes.domain.errors import (
    SolicitudNoEncontradaError,
    SolicitudSinPermisoError,
    TransicionEstadoSolicitudInvalidaError,
)
from modules.solicitudes.infrastructure.api.dependencies import (
    get_cambiar_estado_solicitud_service,
)


class SolicitudEstadoAdapter(SolicitudEstadoPort):
    """Unico punto donde `mantenimientos` cruza a la capa de aplicacion de `solicitudes`:
    aqui se necesita ejecutar una regla de negocio completa (transicion de estado validada,
    permisos, notificacion), no solo leer un dato, asi que reutiliza el servicio real en vez
    de reimplementar la logica contra la coleccion de Mongo."""

    async def marcar_resuelta(self, solicitud_id: str, actor: ActorSolicitud) -> None:
        servicio = get_cambiar_estado_solicitud_service()
        try:
            await servicio.ejecutar(
                CambiarEstadoSolicitudDTO(
                    id_solicitud=solicitud_id,
                    estado_nuevo=EstadoSolicitud.RESUELTA,
                    actor_id=actor.id,
                    actor_nombre=actor.nombre,
                    actor_rol=actor.rol,
                    actor_area_id=actor.area_id,
                    comentario="Resuelta automaticamente al completar el mantenimiento asociado.",
                )
            )
        except (
            SolicitudNoEncontradaError,
            SolicitudSinPermisoError,
            TransicionEstadoSolicitudInvalidaError,
        ):
            # La solicitud ya no existe/no es visible, el actor no tiene permiso para resolverla
            # alla, o ya esta en un estado del que no se puede pasar a 'resuelta' (ej. nunca se
            # puso 'en_proceso'): ninguno de estos casos debe impedir completar el mantenimiento,
            # solo no hay nada que sincronizar automaticamente.
            pass
