from dataclasses import replace

from modules.movimientos.domain.entities import (
    ESTADOS_ITEM_ACTIVOS,
    EstadoItemMovimiento,
    EstadoMovimiento,
    TipoMovimiento,
)


def test_movimiento_es_inmutable(fabrica):
    movimiento = fabrica.movimiento()
    aprobado = replace(movimiento, estado=EstadoMovimiento.APROBADO)

    assert movimiento.estado == EstadoMovimiento.SOLICITADO
    assert aprobado.estado == EstadoMovimiento.APROBADO


def test_movimiento_de_baja_no_tiene_usuario_destino(fabrica):
    movimiento = fabrica.movimiento(tipo=TipoMovimiento.BAJA, usuario_destino_id=None)

    assert movimiento.usuario_destino_id is None


def test_un_movimiento_expone_los_ids_de_sus_activos_y_busca_cada_item(fabrica):
    movimiento = fabrica.movimiento(
        items=[fabrica.item(activo_id="a1"), fabrica.item(activo_id="a2", responsable_original_id="u3")]
    )

    assert movimiento.activo_ids == ["a1", "a2"]
    assert movimiento.item("a2").responsable_original_id == "u3"
    assert movimiento.item("zzz") is None


def test_solo_ocupan_el_activo_los_items_que_siguen_vivos():
    assert EstadoItemMovimiento.PENDIENTE_RESPONSABLE in ESTADOS_ITEM_ACTIVOS
    assert EstadoItemMovimiento.EN_CURSO in ESTADOS_ITEM_ACTIVOS
    assert EstadoItemMovimiento.DEVOLUCION_SOLICITADA in ESTADOS_ITEM_ACTIVOS
    assert EstadoItemMovimiento.RECHAZADO not in ESTADOS_ITEM_ACTIVOS
    assert EstadoItemMovimiento.DEVUELTO not in ESTADOS_ITEM_ACTIVOS
