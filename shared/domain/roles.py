"""Nombres de los roles del sistema y utilidades para preguntar por ellos.

Es la unica fuente de los textos de rol fuera del modulo de usuarios: las reglas de negocio que antes comparaban
con "administrador_general" usan `es_administrador` para que el Super administrador conserve sus capacidades.
"""

ROL_SUPER_ADMINISTRADOR = "super_administrador"
ROL_ADMINISTRADOR_GENERAL = "administrador_general"
ROL_TECNOLOGIA = "tecnologia"
ROL_MANTENIMIENTO = "mantenimiento"
ROL_ADMINISTRATIVO = "administrativo"
ROL_JEFE_AREA = "jefe_area"
ROL_EMPLEADO = "empleado"

# Roles cuya matriz de funciones se puede editar. El Super administrador queda fuera: siempre tiene todo.
ROLES_EDITABLES = (
    ROL_ADMINISTRADOR_GENERAL,
    ROL_TECNOLOGIA,
    ROL_MANTENIMIENTO,
    ROL_ADMINISTRATIVO,
    ROL_JEFE_AREA,
    ROL_EMPLEADO,
)

ETIQUETAS_ROL = {
    ROL_SUPER_ADMINISTRADOR: "Super administrador",
    ROL_ADMINISTRADOR_GENERAL: "Administrador General",
    ROL_TECNOLOGIA: "Tecnología",
    ROL_MANTENIMIENTO: "Mantenimiento",
    ROL_ADMINISTRATIVO: "Administrativo",
    ROL_JEFE_AREA: "Jefe de Área",
    ROL_EMPLEADO: "Empleado",
}

ROLES_ADMINISTRADORES = frozenset({ROL_SUPER_ADMINISTRADOR, ROL_ADMINISTRADOR_GENERAL})


def es_super_administrador(rol: str | None) -> bool:
    """Solo el Super administrador administra permisos y a otros super administradores."""
    return rol == ROL_SUPER_ADMINISTRADOR


def es_administrador(rol: str | None) -> bool:
    """Tiene el poder administrativo sobre los registros de otros: Super administrador o Administrador General."""
    return rol in ROLES_ADMINISTRADORES
