from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    ItemMovimiento,
    TipoMovimiento,
)

_ESTADOS_TERMINALES = {
    EstadoMovimiento.RECHAZADO,
    EstadoMovimiento.DEVUELTO,
    EstadoMovimiento.EJECUTADO,
}

# Estados del item desde los que se puede devolver el activo (lo pidio quien lo tiene, o administracion lo
# recibe sin que se haya pedido).
ESTADOS_ITEM_DEVOLVIBLES = frozenset(
    {EstadoItemMovimiento.EN_CURSO, EstadoItemMovimiento.DEVOLUCION_SOLICITADA}
)


def es_estado_terminal(estado: EstadoMovimiento) -> bool:
    return estado in _ESTADOS_TERMINALES


def calcular_estado(
    tipo: TipoMovimiento, items: list[ItemMovimiento], estado_actual: EstadoMovimiento
) -> EstadoMovimiento:
    """Estado del movimiento a partir del de sus items (la unica fuente de verdad del avance).

    La baja es de un solo activo y la decide administracion: `solicitado` pasa a `aprobado` por una accion
    explicita, asi que aqui solo se reflejan el rechazo y la ejecucion.
    """
    estados = {item.estado for item in items}

    if tipo == TipoMovimiento.BAJA:
        if EstadoItemMovimiento.RECHAZADO in estados:
            return EstadoMovimiento.RECHAZADO
        if EstadoItemMovimiento.EJECUTADO in estados:
            return EstadoMovimiento.EJECUTADO

        return estado_actual

    if EstadoItemMovimiento.PENDIENTE_RESPONSABLE in estados:
        return EstadoMovimiento.SOLICITADO
    if EstadoItemMovimiento.PENDIENTE_ADMIN in estados:
        return EstadoMovimiento.APROBADO_RESPONSABLE
    if estados & ESTADOS_ITEM_DEVOLVIBLES:
        return EstadoMovimiento.EN_CURSO
    if EstadoItemMovimiento.DEVUELTO in estados:
        return EstadoMovimiento.DEVUELTO

    return EstadoMovimiento.RECHAZADO
