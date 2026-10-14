from collections.abc import Iterable

from modules.permisos.domain.errors import (
    PermisoBaseNoDeshabilitableError,
    PermisoDesconocidoError,
    RolDesconocidoError,
    RolNoEditableError,
)
from shared.domain.permisos import CLAVES_BASE, CLAVES_FUNCIONES
from shared.domain.roles import ETIQUETAS_ROL, ROL_SUPER_ADMINISTRADOR, ROLES_EDITABLES


def validar_rol_editable(rol: str) -> None:
    """El Super administrador siempre tiene todo (no se edita) y un rol que no existe no tiene matriz."""
    if rol == ROL_SUPER_ADMINISTRADOR:
        raise RolNoEditableError(rol)

    if rol not in ROLES_EDITABLES:
        raise RolDesconocidoError(rol)


def validar_rol_existente(rol: str) -> None:
    if rol not in ETIQUETAS_ROL:
        raise RolDesconocidoError(rol)


def normalizar_permisos(permisos: Iterable[str]) -> frozenset[str]:
    """Valida la lista pedida: solo funciones del catalogo, y las funciones base no se pueden quitar."""
    pedidos = frozenset(permisos)

    for permiso in sorted(pedidos):
        if permiso not in CLAVES_FUNCIONES:
            raise PermisoDesconocidoError(permiso)

    for base in sorted(CLAVES_BASE):
        if base not in pedidos:
            raise PermisoBaseNoDeshabilitableError(base)

    return pedidos


def calcular_cambios(antes: frozenset[str], despues: frozenset[str]) -> tuple[list[str], list[str]]:
    """(habilitadas, deshabilitadas) al pasar de la matriz anterior a la nueva, en orden estable."""
    return sorted(despues - antes), sorted(antes - despues)
