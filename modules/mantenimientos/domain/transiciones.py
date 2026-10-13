from modules.mantenimientos.domain.entities import EstadoMantenimiento

TRANSICIONES_VALIDAS: dict[EstadoMantenimiento, set[EstadoMantenimiento]] = {
    EstadoMantenimiento.PROGRAMADO: {
        EstadoMantenimiento.EN_PROCESO,
        EstadoMantenimiento.CANCELADO,
    },
    EstadoMantenimiento.EN_PROCESO: {
        EstadoMantenimiento.COMPLETADO,
        EstadoMantenimiento.CANCELADO,
    },
    EstadoMantenimiento.COMPLETADO: set(),
    EstadoMantenimiento.CANCELADO: set(),
}


def es_transicion_valida(desde: EstadoMantenimiento, hacia: EstadoMantenimiento) -> bool:
    return hacia in TRANSICIONES_VALIDAS[desde]


def estados_destino(desde: EstadoMantenimiento) -> list[EstadoMantenimiento]:
    """Estados a los que puede pasar un mantenimiento, en el orden del ciclo de vida."""
    return [estado for estado in EstadoMantenimiento if es_transicion_valida(desde, estado)]
