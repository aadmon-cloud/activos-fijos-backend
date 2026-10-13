import pytest

from modules.movimientos.domain.entities import EstadoItemMovimiento as I
from modules.movimientos.domain.entities import EstadoMovimiento as E
from modules.movimientos.domain.entities import TipoMovimiento
from modules.movimientos.domain.transiciones import calcular_estado, es_estado_terminal


def _items(fabrica, *estados):
    return [fabrica.item(activo_id=f"a{n}", estado=estado) for n, estado in enumerate(estados)]


@pytest.mark.parametrize(
    "estados_items, esperado",
    [
        # Falta algun responsable por decidir: sigue solicitado.
        ([I.PENDIENTE_RESPONSABLE], E.SOLICITADO),
        ([I.PENDIENTE_RESPONSABLE, I.PENDIENTE_ADMIN], E.SOLICITADO),
        ([I.PENDIENTE_RESPONSABLE, I.RECHAZADO], E.SOLICITADO),
        # Todos los responsables decidieron y hay al menos un activo aprobado: espera a administracion.
        ([I.PENDIENTE_ADMIN], E.APROBADO_RESPONSABLE),
        ([I.PENDIENTE_ADMIN, I.RECHAZADO], E.APROBADO_RESPONSABLE),
        # Con activos fuera, esta en curso (aunque otros ya volvieron o se rechazaron).
        ([I.EN_CURSO], E.EN_CURSO),
        ([I.EN_CURSO, I.DEVUELTO, I.RECHAZADO], E.EN_CURSO),
        ([I.DEVOLUCION_SOLICITADA, I.DEVUELTO], E.EN_CURSO),
        # Todo volvio (o fue rechazado, habiendo salido algo).
        ([I.DEVUELTO], E.DEVUELTO),
        ([I.DEVUELTO, I.RECHAZADO], E.DEVUELTO),
        # Nada salio: todo rechazado.
        ([I.RECHAZADO], E.RECHAZADO),
        ([I.RECHAZADO, I.RECHAZADO], E.RECHAZADO),
    ],
)
def test_el_estado_del_prestamo_se_calcula_con_el_de_sus_items(fabrica, estados_items, esperado):
    items = _items(fabrica, *estados_items)

    assert calcular_estado(TipoMovimiento.PRESTAMO, items, E.SOLICITADO) == esperado
    assert calcular_estado(TipoMovimiento.SALIDA_EVENTO, items, E.SOLICITADO) == esperado


def test_la_baja_conserva_su_estado_explicito_mientras_no_se_rechace_ni_ejecute(fabrica):
    items = _items(fabrica, I.PENDIENTE_ADMIN)

    assert calcular_estado(TipoMovimiento.BAJA, items, E.SOLICITADO) == E.SOLICITADO
    assert calcular_estado(TipoMovimiento.BAJA, items, E.APROBADO) == E.APROBADO


def test_la_baja_refleja_el_rechazo_y_la_ejecucion(fabrica):
    assert calcular_estado(TipoMovimiento.BAJA, _items(fabrica, I.RECHAZADO), E.SOLICITADO) == E.RECHAZADO
    assert calcular_estado(TipoMovimiento.BAJA, _items(fabrica, I.EJECUTADO), E.APROBADO) == E.EJECUTADO


@pytest.mark.parametrize(
    "estado, terminal",
    [
        (E.RECHAZADO, True),
        (E.DEVUELTO, True),
        (E.EJECUTADO, True),
        (E.SOLICITADO, False),
        (E.APROBADO_RESPONSABLE, False),
        (E.APROBADO, False),
        (E.EN_CURSO, False),
    ],
)
def test_estados_terminales(estado, terminal):
    assert es_estado_terminal(estado) is terminal
