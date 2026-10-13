from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from modules.notificaciones.application.services.envio import (
    DETALLE_CORREO_NO_CONFIGURADO,
    DETALLE_SIN_DESTINATARIOS,
)
from modules.notificaciones.application.services.enviar_notificacion import (
    EnviarNotificacionService,
)
from modules.notificaciones.application.services.listar_notificaciones import (
    ListarNotificacionesService,
)
from modules.notificaciones.application.services.procesar_recordatorios import (
    ProcesarRecordatoriosService,
)
from modules.notificaciones.application.services.reenviar_notificacion import (
    ReenviarNotificacionService,
)
from modules.notificaciones.domain.entities import EstadoNotificacion, Notificacion
from modules.notificaciones.domain.errors import (
    NotificacionNoEncontradaError,
    NotificacionNoReenviableError,
)
from modules.notificaciones.domain.limites import DESTINATARIOS_MAXIMO
from shared.application.notifications.enlaces import enlace


def _dependencias(correos=("ana@x.com",), configurado=True, url_app="https://activos.org", falla=None):
    repo = AsyncMock()
    repo.guardar.side_effect = lambda n: n if n.id else Notificacion(**{**n.__dict__, "id": "n1"})
    resolutor = AsyncMock()
    resolutor.resolver.return_value = list(correos)
    configuracion = MagicMock()
    configuracion.esta_configurado.return_value = configurado
    configuracion.url_aplicacion.return_value = url_app
    correo = AsyncMock()
    if falla:
        correo.enviar.side_effect = falla

    return repo, resolutor, configuracion, correo


def _enviar(**kwargs):
    repo, resolutor, configuracion, correo = _dependencias(**kwargs)

    return EnviarNotificacionService(repo, resolutor, configuracion, correo), repo, resolutor, correo


async def test_envia_el_correo_y_registra_la_notificacion_como_enviada():
    service, repo, _, correo = _enviar()

    resultado = await service.ejecutar(["usuario:1"], "Asunto", "Cuerpo")

    correo.enviar.assert_awaited_once_with(["ana@x.com"], "Asunto", "Cuerpo", [])
    assert resultado.estado == "enviada"
    assert resultado.correos == ["ana@x.com"]
    assert resultado.detalle is None
    assert resultado.intentos == 1
    assert repo.guardar.await_count == 1


async def test_el_asunto_y_el_cuerpo_se_limpian_antes_de_enviar_y_guardar():
    service, repo, _, correo = _enviar()

    await service.ejecutar(["usuario:1"], "Hola\nBcc: x@y.com", "  Cuerpo  ")

    assert correo.enviar.call_args.args[1] == "Hola Bcc: x@y.com"
    assert repo.guardar.call_args.args[0].cuerpo == "Cuerpo"


async def test_los_enlaces_se_resuelven_con_la_direccion_de_la_aplicacion():
    service, _, _, correo = _enviar(url_app="https://activos.org/")

    await service.ejecutar(["usuario:1"], "A", f"Ver: {enlace('/movimientos/detalle?id=7')}")

    assert correo.enviar.call_args.args[2] == "Ver: https://activos.org/movimientos/detalle?id=7"


async def test_sin_direccion_de_la_aplicacion_el_correo_no_lleva_un_enlace_roto():
    service, _, _, correo = _enviar(url_app=None)

    await service.ejecutar(["usuario:1"], "A", f"Texto\n\nVer: {enlace('/x')}")

    assert correo.enviar.call_args.args[2] == "Texto"


async def test_si_el_envio_falla_queda_fallida_con_el_detalle_y_no_lanza():
    service, repo, _, _ = _enviar(falla=ConnectionError("servidor caido"))

    resultado = await service.ejecutar(["usuario:1"], "A", "C")

    assert resultado.estado == "fallida"
    assert resultado.detalle == "ConnectionError: servidor caido"
    assert repo.guardar.await_count == 1


async def test_si_resolver_los_destinatarios_falla_queda_fallida_y_no_lanza():
    service, repo, resolutor, correo = _enviar()
    resolutor.resolver.side_effect = RuntimeError("base caida")

    resultado = await service.ejecutar(["usuario:1"], "A", "C")

    assert resultado.estado == "fallida"
    correo.enviar.assert_not_called()


async def test_sin_destinatarios_con_correo_queda_omitida_sin_enviar():
    service, _, _, correo = _enviar(correos=())

    resultado = await service.ejecutar(["usuario:1"], "A", "C")

    assert resultado.estado == "omitida"
    assert resultado.detalle == DETALLE_SIN_DESTINATARIOS
    correo.enviar.assert_not_called()


async def test_con_el_correo_sin_configurar_queda_omitida_sin_enviar():
    service, _, _, correo = _enviar(configurado=False)

    resultado = await service.ejecutar(["usuario:1"], "A", "C")

    assert resultado.estado == "omitida"
    assert resultado.detalle == DETALLE_CORREO_NO_CONFIGURADO
    assert resultado.correos == ["ana@x.com"]
    correo.enviar.assert_not_called()


async def test_acota_la_cantidad_de_destinatarios():
    service, _, _, correo = _enviar(correos=[f"u{i}@x.com" for i in range(DESTINATARIOS_MAXIMO + 25)])

    await service.ejecutar(["rol:empleado"], "A", "C")

    assert len(correo.enviar.call_args.args[0]) == DESTINATARIOS_MAXIMO


def _notificacion(**overrides) -> Notificacion:
    valores = dict(
        id="n1",
        destinatarios=["usuario:1"],
        correos=[],
        asunto="Asunto",
        cuerpo="Cuerpo",
        estado=EstadoNotificacion.FALLIDA,
        detalle="ConnectionError: x",
        intentos=1,
        creada_en=datetime(2026, 1, 1, tzinfo=UTC),
        actualizada_en=datetime(2026, 1, 1, tzinfo=UTC),
    )
    valores.update(overrides)

    return Notificacion(**valores)


def _reenviar(notificacion, **kwargs):
    repo, resolutor, configuracion, correo = _dependencias(**kwargs)
    repo.obtener_por_id.return_value = notificacion

    return ReenviarNotificacionService(repo, resolutor, configuracion, correo), repo, correo


@pytest.mark.parametrize("estado", [EstadoNotificacion.FALLIDA, EstadoNotificacion.OMITIDA])
async def test_reenvia_una_fallida_o_omitida_y_cuenta_el_intento(estado):
    service, repo, correo = _reenviar(_notificacion(estado=estado, intentos=2))

    resultado = await service.ejecutar("n1")

    assert resultado.estado == "enviada"
    assert resultado.intentos == 3
    assert resultado.detalle is None
    assert resultado.correos == ["ana@x.com"]
    correo.enviar.assert_awaited_once()
    assert repo.guardar.call_args.args[0].id == "n1"


async def test_reenviar_resuelve_de_nuevo_los_destinatarios():
    repo, resolutor, configuracion, correo = _dependencias()
    repo.obtener_por_id.return_value = _notificacion(destinatarios=["rol:mantenimiento"])
    service = ReenviarNotificacionService(repo, resolutor, configuracion, correo)

    await service.ejecutar("n1")

    resolutor.resolver.assert_awaited_once_with(["rol:mantenimiento"])


async def test_reenviar_si_vuelve_a_fallar_sigue_fallida_con_un_intento_mas():
    service, _, _ = _reenviar(_notificacion(), falla=TimeoutError("sin respuesta"))

    resultado = await service.ejecutar("n1")

    assert resultado.estado == "fallida"
    assert resultado.intentos == 2


async def test_reenviar_una_ya_enviada_falla():
    service, repo, correo = _reenviar(_notificacion(estado=EstadoNotificacion.ENVIADA))

    with pytest.raises(NotificacionNoReenviableError):
        await service.ejecutar("n1")

    correo.enviar.assert_not_called()
    repo.guardar.assert_not_called()


async def test_reenviar_una_inexistente_falla():
    service, _, _ = _reenviar(None)

    with pytest.raises(NotificacionNoEncontradaError):
        await service.ejecutar("n1")


async def test_listar_devuelve_el_total_y_acota_el_limite():
    repo = AsyncMock()
    repo.listar.return_value = [_notificacion()]
    repo.contar.return_value = 41
    service = ListarNotificacionesService(repo)

    listado = await service.ejecutar(EstadoNotificacion.FALLIDA, 10, 99999)

    assert listado.total == 41
    assert listado.limit == 1000
    assert listado.items[0].asunto == "Asunto"
    repo.listar.assert_awaited_once_with(EstadoNotificacion.FALLIDA, 10, 1000)
    repo.contar.assert_awaited_once_with(EstadoNotificacion.FALLIDA)


async def test_procesar_recordatorios_devuelve_lo_que_hizo_cada_tarea():
    mantenimientos, devoluciones = AsyncMock(), AsyncMock()
    mantenimientos.ejecutar.return_value = 3
    devoluciones.ejecutar.return_value = 2

    resultado = await ProcesarRecordatoriosService(mantenimientos, devoluciones).ejecutar()

    assert resultado.mantenimientos_avisados == 3
    assert resultado.devoluciones_recordadas == 2
    assert resultado.errores == []


async def test_si_una_tarea_falla_la_otra_se_ejecuta_y_el_error_queda_en_el_resultado():
    mantenimientos, devoluciones = AsyncMock(), AsyncMock()
    mantenimientos.ejecutar.side_effect = RuntimeError("secreto: no debe filtrarse")
    devoluciones.ejecutar.return_value = 5

    resultado = await ProcesarRecordatoriosService(mantenimientos, devoluciones).ejecutar()

    assert resultado.mantenimientos_avisados is None
    assert resultado.devoluciones_recordadas == 5
    assert resultado.errores == ["mantenimientos: RuntimeError"]
    assert "secreto" not in str(resultado.errores)
