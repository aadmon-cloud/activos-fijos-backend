from modules.solicitudes.domain.entities import EstadoSolicitud

TRANSICIONES_VALIDAS: dict[EstadoSolicitud, set[EstadoSolicitud]] = {
    EstadoSolicitud.PENDIENTE: {EstadoSolicitud.EN_PROCESO, EstadoSolicitud.RECHAZADA},
    EstadoSolicitud.EN_PROCESO: {EstadoSolicitud.RESUELTA, EstadoSolicitud.RECHAZADA},
    EstadoSolicitud.RESUELTA: {EstadoSolicitud.CERRADA},
    EstadoSolicitud.CERRADA: set(),
    EstadoSolicitud.RECHAZADA: set(),
}


def es_transicion_valida(desde: EstadoSolicitud, hacia: EstadoSolicitud) -> bool:
    return hacia in TRANSICIONES_VALIDAS[desde]
