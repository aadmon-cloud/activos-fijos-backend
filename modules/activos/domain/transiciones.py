from modules.activos.domain.entities import EstadoCicloVida

TRANSICIONES_VALIDAS: dict[EstadoCicloVida, set[EstadoCicloVida]] = {
    EstadoCicloVida.DISPONIBLE: {
        EstadoCicloVida.PRESTADO,
        EstadoCicloVida.EN_MANTENIMIENTO,
        EstadoCicloVida.PERDIDO,
        EstadoCicloVida.DANADO,
        EstadoCicloVida.DADO_DE_BAJA,
    },
    EstadoCicloVida.PRESTADO: {
        EstadoCicloVida.DISPONIBLE,
        EstadoCicloVida.PERDIDO,
        EstadoCicloVida.DANADO,
    },
    EstadoCicloVida.EN_MANTENIMIENTO: {
        EstadoCicloVida.DISPONIBLE,
        EstadoCicloVida.DADO_DE_BAJA,
    },
    EstadoCicloVida.DANADO: {
        EstadoCicloVida.EN_MANTENIMIENTO,
        EstadoCicloVida.DADO_DE_BAJA,
    },
    EstadoCicloVida.PERDIDO: {
        EstadoCicloVida.DISPONIBLE,
        EstadoCicloVida.DADO_DE_BAJA,
    },
    EstadoCicloVida.DADO_DE_BAJA: set(),
}


def es_transicion_valida(desde: EstadoCicloVida, hacia: EstadoCicloVida) -> bool:
    return hacia in TRANSICIONES_VALIDAS[desde]
