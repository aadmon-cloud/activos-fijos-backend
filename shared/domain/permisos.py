"""Catalogo de funciones del sistema y la matriz de permisos por defecto de cada rol.

Cada funcion es una accion `[modulo]-[accion]` que se puede habilitar o deshabilitar por rol desde el modulo de
administracion. Es la fuente unica: el frontend recibe el catalogo y la matriz por la API.

La matriz por defecto reproduce exactamente lo que cada rol podia hacer antes de existir la administracion de
permisos, de modo que nada cambia hasta que el Super administrador lo cambie.
"""

from dataclasses import dataclass

from shared.domain.roles import (
    ROL_ADMINISTRADOR_GENERAL,
    ROL_ADMINISTRATIVO,
    ROL_EMPLEADO,
    ROL_JEFE_AREA,
    ROL_MANTENIMIENTO,
    ROL_TECNOLOGIA,
)


@dataclass(frozen=True)
class FuncionSistema:
    clave: str
    modulo: str
    etiqueta: str
    descripcion: str
    # Las funciones base las tiene todo rol y no se pueden apagar: sin ellas el usuario no podria ni entrar.
    es_base: bool = False


# Visible solo para el Super administrador. No se asigna a otros roles ni forma parte de la matriz editable.
PERMISO_ADMINISTRACION_VER = "administracion-ver"
PERMISOS_EXCLUSIVOS_SUPER_ADMINISTRADOR = (PERMISO_ADMINISTRACION_VER,)

FUNCIONES: tuple[FuncionSistema, ...] = (
    FuncionSistema("home-ver", "Inicio", "Ver el inicio", "Entrar a la pantalla de inicio.", es_base=True),
    FuncionSistema("cuenta-ver", "Mi cuenta", "Ver mi cuenta", "Ver y gestionar los datos de la propia cuenta.", es_base=True),
    FuncionSistema("usuarios-ver", "Usuarios", "Ver usuarios", "Consultar el listado y el detalle de los usuarios."),
    FuncionSistema("usuarios-crear", "Usuarios", "Crear usuarios", "Registrar personas nuevas con acceso al sistema."),
    FuncionSistema("usuarios-editar", "Usuarios", "Editar usuarios", "Cambiar nombre, rol, área y teléfono de un usuario."),
    FuncionSistema("usuarios-estado", "Usuarios", "Activar y desactivar usuarios", "Quitar o devolver el acceso a una persona."),
    FuncionSistema("catalogos-ver", "Catálogos", "Ver catálogos", "Consultar áreas, categorías, condiciones, sedes y lugares."),
    FuncionSistema("catalogos-crear", "Catálogos", "Crear en catálogos", "Agregar elementos a los catálogos."),
    FuncionSistema("catalogos-editar", "Catálogos", "Editar catálogos", "Modificar elementos de los catálogos."),
    FuncionSistema("catalogos-eliminar", "Catálogos", "Eliminar de catálogos", "Borrar elementos de los catálogos."),
    FuncionSistema("activos-ver", "Activos", "Ver activos", "Consultar el listado y el detalle de los activos."),
    FuncionSistema("activos-crear", "Activos", "Crear activos", "Registrar activos nuevos."),
    FuncionSistema("activos-editar", "Activos", "Editar activos", "Modificar los datos y la foto de un activo."),
    FuncionSistema("activos-estado", "Activos", "Cambiar el estado de un activo", "Pasar un activo entre sus estados del ciclo de vida."),
    FuncionSistema("solicitudes-ver", "Solicitudes", "Ver solicitudes", "Consultar las solicitudes propias y de su equipo."),
    FuncionSistema("solicitudes-crear", "Solicitudes", "Crear solicitudes", "Registrar solicitudes sobre un activo."),
    FuncionSistema("movimientos-ver", "Movimientos", "Ver movimientos", "Consultar préstamos, salidas a eventos y bajas."),
    FuncionSistema("movimientos-solicitar", "Movimientos", "Solicitar movimientos", "Pedir un préstamo o una salida a evento."),
    FuncionSistema("movimientos-baja", "Movimientos", "Solicitar bajas", "Pedir la baja de un activo."),
    FuncionSistema("movimientos-destinatario", "Movimientos", "Elegir a quién se entrega", "Escoger el destinatario de un activo al prestarlo."),
    FuncionSistema("movimientos-gestionar", "Movimientos", "Gestionar movimientos", "Confirmar salidas y devoluciones y ejecutar bajas."),
    FuncionSistema("mantenimientos-ver", "Mantenimientos", "Ver mantenimientos", "Consultar los mantenimientos de los activos."),
    FuncionSistema("mantenimientos-gestionar", "Mantenimientos", "Gestionar mantenimientos", "Registrar, cambiar de estado, adjuntar archivos y cargar en masa."),
    FuncionSistema("mantenimientos-alertas", "Mantenimientos", "Verificar alertas de mantenimiento", "Lanzar la verificación de mantenimientos próximos."),
    FuncionSistema("mantenimientos-tecnico", "Mantenimientos", "Elegir el técnico", "Escoger quién realiza un mantenimiento."),
    FuncionSistema("notificaciones-ver", "Notificaciones", "Ver notificaciones", "Consultar el historial de notificaciones enviadas."),
    FuncionSistema("notificaciones-gestionar", "Notificaciones", "Reenviar notificaciones", "Volver a enviar una notificación que falló."),
    FuncionSistema("auditorias-ver", "Auditorías", "Ver auditorías", "Consultar auditorías y descargar su reporte."),
    FuncionSistema("auditorias-gestionar", "Auditorías", "Gestionar auditorías", "Crear, verificar y cerrar auditorías de activos."),
    FuncionSistema("dashboard-ver", "Panel", "Ver el panel de indicadores", "Consultar los indicadores generales del sistema."),
)

CLAVES_FUNCIONES: frozenset[str] = frozenset(f.clave for f in FUNCIONES)
CLAVES_BASE: frozenset[str] = frozenset(f.clave for f in FUNCIONES if f.es_base)

_BASE_PARA_TODOS = frozenset(
    {
        "home-ver",
        "cuenta-ver",
        "activos-ver",
        "solicitudes-ver",
        "solicitudes-crear",
        "movimientos-ver",
        "movimientos-solicitar",
    }
)
_MANTENIMIENTO = frozenset({"mantenimientos-ver", "mantenimientos-gestionar"})
_ADMINISTRACION = frozenset(
    {
        "usuarios-ver",
        "usuarios-crear",
        "usuarios-editar",
        "usuarios-estado",
        "catalogos-ver",
        "catalogos-crear",
        "catalogos-editar",
        "catalogos-eliminar",
        "activos-crear",
        "activos-editar",
        "activos-estado",
        "movimientos-baja",
        "movimientos-destinatario",
        "movimientos-gestionar",
        "mantenimientos-alertas",
        "mantenimientos-tecnico",
        "notificaciones-ver",
        "notificaciones-gestionar",
        "auditorias-ver",
        "auditorias-gestionar",
        "dashboard-ver",
    }
)

PERMISOS_POR_DEFECTO: dict[str, frozenset[str]] = {
    ROL_ADMINISTRADOR_GENERAL: _BASE_PARA_TODOS | _MANTENIMIENTO | _ADMINISTRACION,
    ROL_TECNOLOGIA: _BASE_PARA_TODOS,
    ROL_MANTENIMIENTO: _BASE_PARA_TODOS | _MANTENIMIENTO,
    ROL_ADMINISTRATIVO: _BASE_PARA_TODOS,
    ROL_JEFE_AREA: _BASE_PARA_TODOS,
    ROL_EMPLEADO: _BASE_PARA_TODOS,
}


def permisos_por_defecto(rol: str) -> frozenset[str]:
    """Funciones que tiene un rol de fabrica. Un rol desconocido no recibe ninguna (denegar por defecto)."""
    return PERMISOS_POR_DEFECTO.get(rol, frozenset())
