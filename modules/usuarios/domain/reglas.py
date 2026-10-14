from modules.usuarios.domain.entities import RolUsuario
from shared.domain.roles import es_super_administrador

LONGITUD_MINIMA_PASSWORD = 8


def puede_gestionar_rol(actor_rol: str, rol_objetivo: RolUsuario | str) -> bool:
    """Solo un Super administrador asigna el rol de Super administrador o gestiona a quien ya lo tiene.

    Sin esta regla un Administrador General podria ascenderse a si mismo (o desactivar a un Super administrador)
    y saltarse la matriz de permisos que solo el Super administrador controla.
    """
    rol = rol_objetivo.value if isinstance(rol_objetivo, RolUsuario) else rol_objetivo

    if es_super_administrador(rol):
        return es_super_administrador(actor_rol)

    return True
