from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.avisos import EventoMovimiento, avisar, construir_aviso
from modules.movimientos.domain.entities import EstadoItemMovimiento as I
from modules.movimientos.domain.entities import EstadoMovimiento as E
from modules.movimientos.domain.entities import TipoMovimiento
from shared.application.notifications.enlaces import MARCADOR_URL_APP

_ADMIN = "rol:administrador_general"
_SUPER = "rol:super_administrador"


def _activos(fabrica):
    return {
        "a1": fabrica.resumen(id="a1", nombre="Proyector", numero_inventario="INV-1"),
        "a2": fabrica.resumen(id="a2", nombre="Pantalla", numero_inventario="INV-2"),
    }


def _movimiento(fabrica, estados=(I.PENDIENTE_RESPONSABLE,), responsables=("original",), **overrides):
    items = [
        fabrica.item(activo_id=f"a{n}", responsable_original_id=responsable, estado=estado)
        for n, (estado, responsable) in enumerate(zip(estados, responsables, strict=True), start=1)
    ]
    valores = dict(
        items=items,
        creado_por=fabrica.audit("creador", "Luis Perez"),
        usuario_destino_id="destino",
    )
    valores.update(overrides)

    return fabrica.movimiento(**valores)


def test_solicitado_avisa_a_cada_responsable_con_activos_pendientes(fabrica):
    movimiento = _movimiento(
        fabrica, (I.PENDIENTE_RESPONSABLE, I.PENDIENTE_RESPONSABLE), ("r1", "r2")
    )

    aviso = construir_aviso(EventoMovimiento.SOLICITADO, movimiento, _activos(fabrica))

    assert aviso.destinatarios == ["usuario:r1", "usuario:r2"]
    assert "2 activos" in aviso.asunto
    assert "Proyector (INV-1)" in aviso.cuerpo and "Pantalla (INV-2)" in aviso.cuerpo
    assert "Luis Perez" in aviso.cuerpo


def test_solicitado_con_un_solo_activo_lo_nombra_en_el_asunto(fabrica):
    aviso = construir_aviso(EventoMovimiento.SOLICITADO, _movimiento(fabrica), _activos(fabrica))

    assert "Proyector (INV-1)" in aviso.asunto
    assert aviso.destinatarios == ["usuario:original"]


def test_solicitado_sin_responsables_pendientes_avisa_a_administracion(fabrica):
    movimiento = _movimiento(fabrica, (I.PENDIENTE_ADMIN,))

    aviso = construir_aviso(EventoMovimiento.SOLICITADO, movimiento, _activos(fabrica))

    assert aviso.destinatarios == [_ADMIN, _SUPER]


def test_la_baja_solicitada_avisa_a_administracion(fabrica):
    movimiento = _movimiento(fabrica, (I.PENDIENTE_ADMIN,), tipo=TipoMovimiento.BAJA, usuario_destino_id=None)

    aviso = construir_aviso(EventoMovimiento.SOLICITADO, movimiento, _activos(fabrica))

    assert aviso.destinatarios == [_ADMIN, _SUPER]
    assert "baja" in aviso.asunto.lower()


def test_aprobado_por_responsables_avisa_a_administracion_solo_cuando_ya_decidieron_todos(fabrica):
    espera_admin = _movimiento(fabrica, (I.PENDIENTE_ADMIN,), estado=E.APROBADO_RESPONSABLE)
    faltan_otros = _movimiento(fabrica, (I.PENDIENTE_ADMIN, I.PENDIENTE_RESPONSABLE), ("r1", "r2"), estado=E.SOLICITADO)

    completo = construir_aviso(EventoMovimiento.APROBADO_RESPONSABLE, espera_admin, _activos(fabrica))
    parcial = construir_aviso(EventoMovimiento.APROBADO_RESPONSABLE, faltan_otros, _activos(fabrica))

    assert completo.destinatarios == [_ADMIN, _SUPER, "usuario:creador"]
    assert parcial.destinatarios == ["usuario:creador"]


def test_rechazado_avisa_a_los_participantes_con_el_motivo_de_cada_activo(fabrica):
    movimiento = _movimiento(fabrica, (I.RECHAZADO, I.PENDIENTE_ADMIN), ("r1", "r2"))
    rechazado = fabrica.item(activo_id="a1", responsable_original_id="r1", estado=I.RECHAZADO, motivo_rechazo="Lo uso yo")
    movimiento = _movimiento(fabrica, (I.PENDIENTE_ADMIN,), ("r2",), items=[rechazado, movimiento.items[1]])

    aviso = construir_aviso(EventoMovimiento.RECHAZADO, movimiento, _activos(fabrica))

    assert "usuario:creador" in aviso.destinatarios and "usuario:destino" in aviso.destinatarios
    assert "usuario:r1" in aviso.destinatarios
    assert "Lo uso yo" in aviso.cuerpo
    assert "Proyector (INV-1)" in aviso.asunto  # solo el rechazado


def test_salida_confirmada_menciona_solo_lo_que_salio_y_el_comprobante(fabrica):
    movimiento = _movimiento(fabrica, (I.EN_CURSO, I.RECHAZADO), ("r1", "r2"), comprobante_archivo_id="f1")

    aviso = construir_aviso(EventoMovimiento.SALIDA_CONFIRMADA, movimiento, _activos(fabrica))

    assert "Proyector" in aviso.cuerpo
    assert "Pantalla" not in aviso.cuerpo
    assert "comprobante" in aviso.cuerpo.lower()


def test_devolucion_solicitada_avisa_a_administracion(fabrica):
    movimiento = _movimiento(fabrica, (I.DEVOLUCION_SOLICITADA,))

    aviso = construir_aviso(EventoMovimiento.DEVOLUCION_SOLICITADA, movimiento, _activos(fabrica))

    assert aviso.destinatarios[:2] == [_ADMIN, _SUPER]
    assert "Proyector" in aviso.cuerpo


def test_devolucion_confirmada_lista_las_novedades(fabrica):
    item = fabrica.item(activo_id="a1", estado=I.DEVUELTO, novedad_devolucion="Pantalla rayada")
    movimiento = _movimiento(fabrica, items=[item])

    aviso = construir_aviso(EventoMovimiento.DEVOLUCION_CONFIRMADA, movimiento, _activos(fabrica))

    assert "Pantalla rayada" in aviso.cuerpo
    assert "usuario:destino" in aviso.destinatarios


def test_devolucion_confirmada_sin_novedades_no_menciona_novedades(fabrica):
    item = fabrica.item(activo_id="a1", estado=I.DEVUELTO)
    aviso = construir_aviso(EventoMovimiento.DEVOLUCION_CONFIRMADA, _movimiento(fabrica, items=[item]), _activos(fabrica))

    assert "Novedades" not in aviso.cuerpo


def test_baja_ejecutada_avisa_a_administracion_y_participantes(fabrica):
    movimiento = _movimiento(fabrica, (I.EJECUTADO,), tipo=TipoMovimiento.BAJA, usuario_destino_id=None)

    aviso = construir_aviso(EventoMovimiento.BAJA_EJECUTADA, movimiento, _activos(fabrica))

    assert aviso.destinatarios[:2] == [_ADMIN, _SUPER]
    assert "usuario:original" in aviso.destinatarios


def test_recordatorio_incluye_la_fecha_estimada(fabrica):
    movimiento = _movimiento(
        fabrica, (I.EN_CURSO,), fecha_retorno_estimada=datetime(2026, 5, 2, tzinfo=UTC), estado=E.EN_CURSO
    )

    aviso = construir_aviso(EventoMovimiento.RECORDATORIO_DEVOLUCION, movimiento, _activos(fabrica))

    assert "02/05/2026" in aviso.cuerpo


def test_el_evento_se_nombra_en_el_cuerpo_y_lleva_enlace(fabrica):
    movimiento = _movimiento(fabrica, tipo=TipoMovimiento.SALIDA_EVENTO, evento_nombre="Feria del libro")

    aviso = construir_aviso(EventoMovimiento.SOLICITADO, movimiento, _activos(fabrica))

    assert "Feria del libro" in aviso.cuerpo
    assert MARCADOR_URL_APP in aviso.cuerpo
    assert "/movimientos/detalle?id=m1" in aviso.cuerpo


def test_una_lista_larga_de_activos_se_resume(fabrica):
    estados = tuple(I.PENDIENTE_RESPONSABLE for _ in range(12))
    movimiento = _movimiento(fabrica, estados, tuple("r" for _ in range(12)))

    aviso = construir_aviso(EventoMovimiento.SOLICITADO, movimiento, {})

    assert "y 4 mas" in aviso.cuerpo
    assert "12 activos" in aviso.asunto


def test_los_destinatarios_no_se_repiten(fabrica):
    movimiento = _movimiento(fabrica, (I.PENDIENTE_ADMIN,), ("creador",), usuario_destino_id="creador")

    aviso = construir_aviso(EventoMovimiento.APROBADO, movimiento, _activos(fabrica))

    assert aviso.destinatarios == ["usuario:creador"]


@pytest.mark.parametrize("evento", list(EventoMovimiento))
def test_todos_los_eventos_tienen_asunto_cuerpo_y_destinatarios(fabrica, evento):
    movimiento = _movimiento(fabrica, (I.EN_CURSO,), estado=E.EN_CURSO)

    aviso = construir_aviso(evento, movimiento, _activos(fabrica))

    assert aviso.asunto and aviso.cuerpo and aviso.destinatarios


async def test_avisar_entrega_el_aviso_al_notificador(fabrica):
    notificador = AsyncMock()

    await avisar(notificador, EventoMovimiento.SOLICITADO, _movimiento(fabrica), _activos(fabrica))

    kwargs = notificador.notificar.await_args.kwargs
    assert kwargs["destinatarios"] == ["usuario:original"]
    assert kwargs["asunto"] and kwargs["cuerpo"]
