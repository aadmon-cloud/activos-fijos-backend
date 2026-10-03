from modules.solicitudes.domain.entities import Solicitud

_ROL_ADMINISTRADOR_GENERAL = "administrador_general"


def puede_gestionar(
    solicitud: Solicitud,
    actor_id: str,
    actor_rol: str,
    actor_area_id: str | None,
) -> bool:
    if actor_rol == _ROL_ADMINISTRADOR_GENERAL:
        return True
    if actor_id == solicitud.creado_por.id_persona:
        return True
    if solicitud.rol_asignado is not None and actor_rol == solicitud.rol_asignado:
        return True
    if (
        solicitud.area_id is not None
        and actor_area_id is not None
        and actor_area_id == solicitud.area_id
    ):
        return True
    return False
