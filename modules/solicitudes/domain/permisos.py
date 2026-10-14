from modules.solicitudes.domain.entities import EstadoSolicitud, Solicitud
from modules.solicitudes.domain.transiciones import TRANSICIONES_VALIDAS
from shared.domain.roles import es_administrador as es_rol_administrador


def es_administrador(actor_rol: str) -> bool:
    return es_rol_administrador(actor_rol)


def es_solicitante(solicitud: Solicitud, actor_id: str) -> bool:
    return actor_id == solicitud.creado_por.id_persona


def es_equipo_asignado(
    solicitud: Solicitud, actor_rol: str, actor_area_id: str | None
) -> bool:
    """El rol o el area a la que el sistema asigno la solicitud (quienes la atienden)."""
    if solicitud.rol_asignado is not None and actor_rol == solicitud.rol_asignado:
        return True

    return (
        solicitud.area_id is not None
        and actor_area_id is not None
        and actor_area_id == solicitud.area_id
    )


def puede_ver(
    solicitud: Solicitud, actor_id: str, actor_rol: str, actor_area_id: str | None
) -> bool:
    """Ve la solicitud su solicitante, el equipo al que se asigno y el administrador general."""
    return (
        es_administrador(actor_rol)
        or es_solicitante(solicitud, actor_id)
        or es_equipo_asignado(solicitud, actor_rol, actor_area_id)
    )


def puede_procesar(
    solicitud: Solicitud, actor_id: str, actor_rol: str, actor_area_id: str | None
) -> bool:
    """Atender la solicitud (iniciarla, resolverla o rechazarla).

    Es del equipo asignado y del administrador. El solicitante NO puede procesar su propia
    solicitud, ni siquiera si pertenece al equipo asignado: nadie aprueba lo que pidio.
    """
    if es_administrador(actor_rol):
        return True

    return es_equipo_asignado(solicitud, actor_rol, actor_area_id) and not es_solicitante(
        solicitud, actor_id
    )


def puede_cerrar(solicitud: Solicitud, actor_id: str, actor_rol: str) -> bool:
    """Confirmar y cerrar una solicitud ya resuelta: lo hace quien la pidio (o el administrador)."""
    return es_administrador(actor_rol) or es_solicitante(solicitud, actor_id)


def puede_comentar(
    solicitud: Solicitud, actor_id: str, actor_rol: str, actor_area_id: str | None
) -> bool:
    return puede_ver(solicitud, actor_id, actor_rol, actor_area_id)


def puede_cambiar_a(
    solicitud: Solicitud,
    estado_nuevo: EstadoSolicitud,
    actor_id: str,
    actor_rol: str,
    actor_area_id: str | None,
) -> bool:
    """Si el actor tiene permiso para llevar la solicitud al estado indicado (sin validar la transicion)."""
    if estado_nuevo == EstadoSolicitud.CERRADA:
        return puede_cerrar(solicitud, actor_id, actor_rol)

    return puede_procesar(solicitud, actor_id, actor_rol, actor_area_id)


def estados_destino_permitidos(
    solicitud: Solicitud, actor_id: str, actor_rol: str, actor_area_id: str | None
) -> list[EstadoSolicitud]:
    """Estados a los que este actor puede llevar la solicitud ahora (transicion valida Y permiso)."""
    validos = TRANSICIONES_VALIDAS[solicitud.estado]

    return [
        estado
        for estado in EstadoSolicitud
        if estado in validos
        and puede_cambiar_a(solicitud, estado, actor_id, actor_rol, actor_area_id)
    ]
