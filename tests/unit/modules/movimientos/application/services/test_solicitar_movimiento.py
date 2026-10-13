from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from modules.movimientos.application.dto.solicitar_movimiento_dto import SolicitarMovimientoDTO
from modules.movimientos.application.services.solicitar_movimiento import (
    SolicitarMovimientoService,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    SentidoPrestamo,
    TipoMovimiento,
)
from modules.movimientos.domain.errors import (
    ActivoNoDisponibleError,
    ActivoNoEncontradoParaMovimientoError,
    ActivosMovimientoObligatoriosError,
    BajaDeUnSoloActivoError,
    DescripcionMovimientoVaciaError,
    DestinatarioIgualAlResponsableError,
    DestinatarioNoPermitidoError,
    EventoNombreObligatorioError,
    FechasMovimientoInvalidasError,
    MovimientoActivoYaExisteError,
    NoEsResponsableDelActivoError,
    SentidoPrestamoObligatorioError,
    SolicitudDeBajaRequiereAdminError,
    UsuarioDestinoNoEncontradoError,
    UsuarioDestinoObligatorioError,
)


def _dto(**overrides) -> SolicitarMovimientoDTO:
    valores = dict(
        tipo=TipoMovimiento.PRESTAMO,
        sentido=SentidoPrestamo.SOLICITAR,
        activo_ids=["a1"],
        descripcion="Necesito el proyector",
        solicitante_id="u2",
        solicitante_nombre="Solicitante",
        solicitante_rol="empleado",
    )
    valores.update(overrides)
    return SolicitarMovimientoDTO(**valores)


def _servicio(fabrica, resumenes=None, usuario_existe=True, ocupados=()):
    repo = AsyncMock()
    repo.activos_ocupados.return_value = set(ocupados)
    repo.guardar.side_effect = lambda m: m
    activo_movimiento = AsyncMock()
    activo_movimiento.obtener_resumenes.return_value = (
        resumenes if resumenes is not None else {"a1": fabrica.resumen()}
    )
    verificador = AsyncMock()
    verificador.existe.return_value = usuario_existe
    notificador = AsyncMock()

    return SolicitarMovimientoService(repo, activo_movimiento, verificador, notificador), repo, notificador


def _resumenes(fabrica, **por_activo):
    return {
        activo_id: fabrica.resumen(id=activo_id, **datos) for activo_id, datos in por_activo.items()
    }


# --- varios activos y estado inicial ---


async def test_solicitar_varios_activos_crea_un_item_por_activo(fabrica):
    resumenes = _resumenes(fabrica, a1={"responsable_id": "u1"}, a2={"responsable_id": "u3"})
    service, repo, _ = _servicio(fabrica, resumenes)

    await service.ejecutar(_dto(activo_ids=["a1", "a2"]))

    movimiento = repo.guardar.call_args.args[0]
    assert movimiento.activo_ids == ["a1", "a2"]
    assert [i.responsable_original_id for i in movimiento.items] == ["u1", "u3"]
    assert all(i.estado == EstadoItemMovimiento.PENDIENTE_RESPONSABLE for i in movimiento.items)
    assert movimiento.estado == EstadoMovimiento.SOLICITADO
    assert movimiento.usuario_destino_id == "u2"


async def test_los_activos_repetidos_se_piden_una_sola_vez(fabrica):
    service, repo, _ = _servicio(fabrica)

    await service.ejecutar(_dto(activo_ids=["a1", "a1"]))

    assert repo.guardar.call_args.args[0].activo_ids == ["a1"]


async def test_si_quien_pide_ya_es_el_responsable_ese_activo_espera_a_administracion(fabrica):
    resumenes = _resumenes(fabrica, a1={"responsable_id": "u2"}, a2={"responsable_id": "u3"})
    service, repo, _ = _servicio(fabrica, resumenes)

    await service.ejecutar(_dto(activo_ids=["a1", "a2"]))

    items = repo.guardar.call_args.args[0].items
    assert [i.estado for i in items] == [
        EstadoItemMovimiento.PENDIENTE_ADMIN,
        EstadoItemMovimiento.PENDIENTE_RESPONSABLE,
    ]


async def test_si_ningun_responsable_debe_decidir_el_movimiento_espera_a_administracion(fabrica):
    resumenes = _resumenes(fabrica, a1={"responsable_id": "u2"})
    service, repo, _ = _servicio(fabrica, resumenes)

    await service.ejecutar(_dto())

    assert repo.guardar.call_args.args[0].estado == EstadoMovimiento.APROBADO_RESPONSABLE


async def test_avisa_a_los_responsables_pendientes(fabrica):
    service, _, notificador = _servicio(fabrica)

    await service.ejecutar(_dto())

    assert notificador.notificar.await_args.kwargs["destinatarios"] == ["usuario:u1"]


# --- prestamo en dos sentidos ---


async def test_prestamo_sin_sentido_falla(fabrica):
    service, repo, _ = _servicio(fabrica)

    with pytest.raises(SentidoPrestamoObligatorioError):
        await service.ejecutar(_dto(sentido=None))

    repo.guardar.assert_not_called()


async def test_al_solicitar_un_prestamo_el_destinatario_es_quien_lo_pide(fabrica):
    service, repo, _ = _servicio(fabrica)

    await service.ejecutar(_dto(usuario_destino_id=None))

    assert repo.guardar.call_args.args[0].usuario_destino_id == "u2"


async def test_al_solicitar_un_prestamo_un_empleado_no_puede_elegir_otro_destinatario(fabrica):
    service, repo, _ = _servicio(fabrica)

    with pytest.raises(DestinatarioNoPermitidoError):
        await service.ejecutar(_dto(usuario_destino_id="u9"))

    repo.guardar.assert_not_called()


async def test_un_administrador_puede_montar_la_solicitud_para_otro_destinatario(fabrica):
    service, repo, _ = _servicio(fabrica)

    await service.ejecutar(_dto(solicitante_rol="administrador_general", usuario_destino_id="u9"))

    assert repo.guardar.call_args.args[0].usuario_destino_id == "u9"


async def test_prestar_un_activo_propio_a_otro_usuario(fabrica):
    resumenes = _resumenes(fabrica, a1={"responsable_id": "u2"})
    service, repo, _ = _servicio(fabrica, resumenes)

    await service.ejecutar(_dto(sentido=SentidoPrestamo.PRESTAR, usuario_destino_id="u5"))

    movimiento = repo.guardar.call_args.args[0]
    assert movimiento.sentido == SentidoPrestamo.PRESTAR
    assert movimiento.usuario_destino_id == "u5"
    assert movimiento.items[0].estado == EstadoItemMovimiento.PENDIENTE_ADMIN


async def test_prestar_exige_indicar_a_quien(fabrica):
    resumenes = _resumenes(fabrica, a1={"responsable_id": "u2"})
    service, _, _ = _servicio(fabrica, resumenes)

    with pytest.raises(UsuarioDestinoObligatorioError):
        await service.ejecutar(_dto(sentido=SentidoPrestamo.PRESTAR, usuario_destino_id=None))


async def test_un_empleado_no_presta_activos_de_otro(fabrica):
    service, repo, _ = _servicio(fabrica)  # el activo es de u1, quien pide es u2

    with pytest.raises(NoEsResponsableDelActivoError):
        await service.ejecutar(_dto(sentido=SentidoPrestamo.PRESTAR, usuario_destino_id="u5"))

    repo.guardar.assert_not_called()


async def test_un_administrador_puede_prestar_activos_de_otro_que_aprobara_su_responsable(fabrica):
    service, repo, _ = _servicio(fabrica)

    await service.ejecutar(
        _dto(sentido=SentidoPrestamo.PRESTAR, usuario_destino_id="u5", solicitante_rol="administrador_general")
    )

    assert repo.guardar.call_args.args[0].items[0].estado == EstadoItemMovimiento.PENDIENTE_RESPONSABLE


async def test_no_se_presta_un_activo_a_su_propio_responsable(fabrica):
    service, _, _ = _servicio(fabrica)

    with pytest.raises(DestinatarioIgualAlResponsableError):
        await service.ejecutar(
            _dto(sentido=SentidoPrestamo.PRESTAR, usuario_destino_id="u1", solicitante_rol="administrador_general")
        )


# --- salida a evento ---


async def test_salida_a_evento_con_varios_activos(fabrica):
    resumenes = _resumenes(fabrica, a1={"responsable_id": "u1"}, a2={"responsable_id": "u1"})
    service, repo, _ = _servicio(fabrica, resumenes)

    await service.ejecutar(
        _dto(
            tipo=TipoMovimiento.SALIDA_EVENTO,
            sentido=None,
            activo_ids=["a1", "a2"],
            evento_nombre="Feria",
            fecha_salida_estimada=datetime.now(UTC),
            fecha_retorno_estimada=datetime.now(UTC) + timedelta(days=2),
        )
    )

    movimiento = repo.guardar.call_args.args[0]
    assert movimiento.evento_nombre == "Feria"
    assert movimiento.sentido is None
    assert movimiento.usuario_destino_id == "u2"
    assert len(movimiento.items) == 2


async def test_salida_a_evento_sin_nombre_falla(fabrica):
    service, _, _ = _servicio(fabrica)

    with pytest.raises(EventoNombreObligatorioError):
        await service.ejecutar(_dto(tipo=TipoMovimiento.SALIDA_EVENTO, sentido=None, evento_nombre="  "))


async def test_retorno_anterior_a_la_salida_falla(fabrica):
    service, _, _ = _servicio(fabrica)
    ahora = datetime.now(UTC)

    with pytest.raises(FechasMovimientoInvalidasError):
        await service.ejecutar(
            _dto(fecha_salida_estimada=ahora, fecha_retorno_estimada=ahora - timedelta(days=1))
        )


# --- baja ---


async def test_solicitar_baja_sin_rol_admin_falla(fabrica):
    service, repo, _ = _servicio(fabrica)

    with pytest.raises(SolicitudDeBajaRequiereAdminError):
        await service.ejecutar(_dto(tipo=TipoMovimiento.BAJA, sentido=None))

    repo.guardar.assert_not_called()


async def test_solicitar_baja_con_rol_admin_espera_a_administracion_sin_destino(fabrica):
    service, repo, notificador = _servicio(fabrica)

    await service.ejecutar(
        _dto(tipo=TipoMovimiento.BAJA, sentido=None, solicitante_rol="administrador_general")
    )

    movimiento = repo.guardar.call_args.args[0]
    assert movimiento.usuario_destino_id is None
    assert movimiento.items[0].estado == EstadoItemMovimiento.PENDIENTE_ADMIN
    assert movimiento.estado == EstadoMovimiento.SOLICITADO
    assert notificador.notificar.await_args.kwargs["destinatarios"] == ["rol:administrador_general"]


async def test_la_baja_es_de_un_solo_activo(fabrica):
    resumenes = _resumenes(fabrica, a1={}, a2={})
    service, _, _ = _servicio(fabrica, resumenes)

    with pytest.raises(BajaDeUnSoloActivoError):
        await service.ejecutar(
            _dto(
                tipo=TipoMovimiento.BAJA,
                sentido=None,
                activo_ids=["a1", "a2"],
                solicitante_rol="administrador_general",
            )
        )


# --- validaciones comunes ---


async def test_sin_activos_falla(fabrica):
    service, _, _ = _servicio(fabrica)

    with pytest.raises(ActivosMovimientoObligatoriosError):
        await service.ejecutar(_dto(activo_ids=[]))


async def test_descripcion_vacia_falla(fabrica):
    service, _, _ = _servicio(fabrica)

    with pytest.raises(DescripcionMovimientoVaciaError):
        await service.ejecutar(_dto(descripcion="   "))


async def test_un_activo_inexistente_falla(fabrica):
    service, _, _ = _servicio(fabrica, resumenes={})

    with pytest.raises(ActivoNoEncontradoParaMovimientoError):
        await service.ejecutar(_dto())


async def test_un_activo_que_no_esta_disponible_falla(fabrica):
    resumenes = _resumenes(fabrica, a1={"estado_ciclo_vida": "prestado"})
    service, repo, _ = _servicio(fabrica, resumenes)

    with pytest.raises(ActivoNoDisponibleError):
        await service.ejecutar(_dto())

    repo.guardar.assert_not_called()


async def test_un_activo_con_otro_movimiento_sin_terminar_falla(fabrica):
    service, repo, _ = _servicio(fabrica, ocupados={"a1"})

    with pytest.raises(MovimientoActivoYaExisteError):
        await service.ejecutar(_dto())

    repo.guardar.assert_not_called()


async def test_un_destinatario_inexistente_falla(fabrica):
    service, _, _ = _servicio(fabrica, usuario_existe=False)

    with pytest.raises(UsuarioDestinoNoEncontradoError):
        await service.ejecutar(_dto())
