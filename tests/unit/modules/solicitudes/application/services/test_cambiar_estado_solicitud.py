from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from modules.solicitudes.application.dto.cambiar_estado_solicitud_dto import (
    CambiarEstadoSolicitudDTO,
)
from modules.solicitudes.application.services.cambiar_estado_solicitud import (
    CambiarEstadoSolicitudService,
)
from modules.solicitudes.domain.entities import EstadoSolicitud, PrioridadSolicitud, Solicitud, TipoSolicitud
from modules.solicitudes.domain.errors import (
    SolicitudNoEncontradaError,
    SolicitudSinPermisoError,
    TransicionEstadoSolicitudInvalidaError,
)
from shared.domain.entities.audit import AuditPersona


def _solicitud(estado: EstadoSolicitud = EstadoSolicitud.PENDIENTE) -> Solicitud:
    return Solicitud(
        id="1",
        tipo=TipoSolicitud.MANTENIMIENTO,
        activo_id="a1",
        descripcion="desc",
        prioridad=PrioridadSolicitud.MEDIA,
        evidencias=[],
        estado=estado,
        rol_asignado="mantenimiento",
        area_id=None,
        seguimiento=[],
        creado_por=AuditPersona(id_persona="solicitante-1", nombre="Ana", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


def _activo_estado(estado_actual="disponible", cambia=True):
    mock = AsyncMock()
    mock.obtener_estado.return_value = estado_actual
    mock.cambiar_estado.return_value = cambia

    return mock


def _servicio(repositorio, notificador, activo_estado=None):
    return CambiarEstadoSolicitudService(
        repositorio, notificador, activo_estado if activo_estado is not None else _activo_estado()
    )


@pytest.fixture
def repositorio_mock():
    mock = AsyncMock()
    mock.obtener_por_id.return_value = _solicitud()
    mock.guardar.side_effect = lambda solicitud: solicitud
    return mock


@pytest.fixture
def notificador_mock():
    return AsyncMock()


async def test_cambiar_estado_aplica_transicion_valida_y_agrega_seguimiento(
    repositorio_mock, notificador_mock
):
    service = _servicio(repositorio_mock, notificador_mock)

    resultado = await service.ejecutar(
        CambiarEstadoSolicitudDTO(
            id_solicitud="1",
            estado_nuevo=EstadoSolicitud.EN_PROCESO,
            actor_id="mantenimiento-1",
            actor_nombre="Tecnico",
            actor_rol="mantenimiento",
            actor_area_id=None,
        )
    )

    assert resultado.estado == EstadoSolicitud.EN_PROCESO.value
    # El cambio de estado y la nota de que el activo paso a "En mantenimiento".
    assert len(resultado.seguimiento) == 2
    notificador_mock.notificar.assert_called_once()


async def test_cambiar_estado_lanza_error_si_la_transicion_es_invalida(
    repositorio_mock, notificador_mock
):
    repositorio_mock.obtener_por_id.return_value = _solicitud(EstadoSolicitud.CERRADA)
    service = _servicio(repositorio_mock, notificador_mock)

    with pytest.raises(TransicionEstadoSolicitudInvalidaError):
        await service.ejecutar(
            CambiarEstadoSolicitudDTO(
                id_solicitud="1",
                estado_nuevo=EstadoSolicitud.PENDIENTE,
                actor_id="mantenimiento-1",
                actor_nombre="Tecnico",
                actor_rol="mantenimiento",
                actor_area_id=None,
            )
        )

    repositorio_mock.guardar.assert_not_called()


async def test_cambiar_estado_responde_no_encontrada_si_el_usuario_no_puede_ver_la_solicitud(
    repositorio_mock, notificador_mock
):
    service = _servicio(repositorio_mock, notificador_mock)

    with pytest.raises(SolicitudNoEncontradaError):
        await service.ejecutar(
            CambiarEstadoSolicitudDTO(
                id_solicitud="1",
                estado_nuevo=EstadoSolicitud.EN_PROCESO,
                actor_id="desconocido",
                actor_nombre="X",
                actor_rol="tecnologia",
                actor_area_id="otra-area",
            )
        )

    repositorio_mock.guardar.assert_not_called()


async def test_cambiar_estado_lanza_error_si_no_existe(repositorio_mock, notificador_mock):
    repositorio_mock.obtener_por_id.return_value = None
    service = _servicio(repositorio_mock, notificador_mock)

    with pytest.raises(SolicitudNoEncontradaError):
        await service.ejecutar(
            CambiarEstadoSolicitudDTO(
                id_solicitud="1",
                estado_nuevo=EstadoSolicitud.EN_PROCESO,
                actor_id="solicitante-1",
                actor_nombre="Ana",
                actor_rol="empleado",
                actor_area_id=None,
            )
        )


def _dto_estado(estado, actor_id, rol, area=None) -> CambiarEstadoSolicitudDTO:
    return CambiarEstadoSolicitudDTO(
        id_solicitud="1",
        estado_nuevo=estado,
        actor_id=actor_id,
        actor_nombre="Actor",
        actor_rol=rol,
        actor_area_id=area,
    )


async def test_el_solicitante_no_puede_procesar_su_propia_solicitud(repositorio_mock, notificador_mock):
    service = _servicio(repositorio_mock, notificador_mock)

    for destino in (EstadoSolicitud.EN_PROCESO, EstadoSolicitud.RECHAZADA):
        with pytest.raises(SolicitudSinPermisoError):
            await service.ejecutar(_dto_estado(destino, "solicitante-1", "empleado"))

    repositorio_mock.guardar.assert_not_called()


async def test_el_solicitante_cierra_una_solicitud_resuelta(repositorio_mock, notificador_mock):
    repositorio_mock.obtener_por_id.return_value = _solicitud(EstadoSolicitud.RESUELTA)
    service = _servicio(repositorio_mock, notificador_mock)

    resultado = await service.ejecutar(
        _dto_estado(EstadoSolicitud.CERRADA, "solicitante-1", "empleado")
    )

    assert resultado.estado == EstadoSolicitud.CERRADA.value


async def test_el_equipo_asignado_no_puede_cerrar_una_solicitud_resuelta(
    repositorio_mock, notificador_mock
):
    repositorio_mock.obtener_por_id.return_value = _solicitud(EstadoSolicitud.RESUELTA)
    service = _servicio(repositorio_mock, notificador_mock)

    with pytest.raises(SolicitudSinPermisoError):
        await service.ejecutar(_dto_estado(EstadoSolicitud.CERRADA, "tecnico-1", "mantenimiento"))


async def test_el_administrador_puede_aplicar_cualquier_transicion_valida(
    repositorio_mock, notificador_mock
):
    service = _servicio(repositorio_mock, notificador_mock)

    resultado = await service.ejecutar(
        _dto_estado(EstadoSolicitud.RECHAZADA, "admin-1", "administrador_general")
    )

    assert resultado.estado == EstadoSolicitud.RECHAZADA.value


def _solicitud_de(tipo: TipoSolicitud, estado: EstadoSolicitud) -> Solicitud:
    from dataclasses import replace

    return replace(_solicitud(estado), tipo=tipo)


async def test_aceptar_un_mantenimiento_pone_el_activo_en_mantenimiento(
    repositorio_mock, notificador_mock
):
    activo = _activo_estado("disponible")
    service = _servicio(repositorio_mock, notificador_mock, activo)

    resultado = await service.ejecutar(
        _dto_estado(EstadoSolicitud.EN_PROCESO, "tecnico-1", "mantenimiento")
    )

    activo.cambiar_estado.assert_awaited_once_with("a1", "en_mantenimiento", "tecnico-1", "Actor")
    assert len(resultado.seguimiento) == 2
    assert "de 'Disponible' a 'En mantenimiento'" in resultado.seguimiento[1].comentario
    assert resultado.seguimiento[1].estado_nuevo is None


async def test_resolver_un_mantenimiento_devuelve_el_activo_a_disponible(
    repositorio_mock, notificador_mock
):
    repositorio_mock.obtener_por_id.return_value = _solicitud(EstadoSolicitud.EN_PROCESO)
    activo = _activo_estado("en_mantenimiento")
    service = _servicio(repositorio_mock, notificador_mock, activo)

    await service.ejecutar(_dto_estado(EstadoSolicitud.RESUELTA, "tecnico-1", "mantenimiento"))

    activo.cambiar_estado.assert_awaited_once_with("a1", "disponible", "tecnico-1", "Actor")


async def test_resolver_no_toca_el_activo_si_ya_no_esta_en_mantenimiento(
    repositorio_mock, notificador_mock
):
    repositorio_mock.obtener_por_id.return_value = _solicitud(EstadoSolicitud.EN_PROCESO)
    activo = _activo_estado("dado_de_baja")
    service = _servicio(repositorio_mock, notificador_mock, activo)

    resultado = await service.ejecutar(
        _dto_estado(EstadoSolicitud.RESUELTA, "tecnico-1", "mantenimiento")
    )

    activo.cambiar_estado.assert_not_called()
    assert len(resultado.seguimiento) == 1


@pytest.mark.parametrize(
    "tipo, esperado",
    [(TipoSolicitud.REPORTE_DANO, "danado"), (TipoSolicitud.REPORTE_PERDIDA, "perdido")],
)
async def test_aceptar_un_reporte_marca_el_activo(repositorio_mock, notificador_mock, tipo, esperado):
    repositorio_mock.obtener_por_id.return_value = _solicitud_de(tipo, EstadoSolicitud.PENDIENTE)
    repositorio_mock.obtener_por_id.return_value = _con_area(repositorio_mock.obtener_por_id.return_value)
    activo = _activo_estado("disponible")
    service = _servicio(repositorio_mock, notificador_mock, activo)

    await service.ejecutar(_dto_estado(EstadoSolicitud.EN_PROCESO, "admin-1", "administrador_general"))

    activo.cambiar_estado.assert_awaited_once_with("a1", esperado, "admin-1", "Actor")


def _con_area(solicitud: Solicitud) -> Solicitud:
    from dataclasses import replace

    return replace(solicitud, rol_asignado=None, area_id="area-1")


async def test_rechazar_no_cambia_el_activo(repositorio_mock, notificador_mock):
    activo = _activo_estado("disponible")
    service = _servicio(repositorio_mock, notificador_mock, activo)

    await service.ejecutar(_dto_estado(EstadoSolicitud.RECHAZADA, "tecnico-1", "mantenimiento"))

    activo.obtener_estado.assert_not_called()
    activo.cambiar_estado.assert_not_called()


async def test_un_cambio_de_tipo_cambio_no_toca_el_activo(repositorio_mock, notificador_mock):
    repositorio_mock.obtener_por_id.return_value = replace_rol(
        _solicitud_de(TipoSolicitud.CAMBIO, EstadoSolicitud.PENDIENTE), "tecnologia"
    )
    activo = _activo_estado("disponible")
    service = _servicio(repositorio_mock, notificador_mock, activo)

    await service.ejecutar(_dto_estado(EstadoSolicitud.EN_PROCESO, "tec-1", "tecnologia"))

    activo.cambiar_estado.assert_not_called()


def replace_rol(solicitud: Solicitud, rol: str) -> Solicitud:
    from dataclasses import replace

    return replace(solicitud, rol_asignado=rol)


async def test_si_la_transicion_del_activo_no_es_valida_la_solicitud_avanza_y_lo_deja_anotado(
    repositorio_mock, notificador_mock
):
    activo = _activo_estado("prestado", cambia=False)
    service = _servicio(repositorio_mock, notificador_mock, activo)

    resultado = await service.ejecutar(
        _dto_estado(EstadoSolicitud.EN_PROCESO, "tecnico-1", "mantenimiento")
    )

    assert resultado.estado == EstadoSolicitud.EN_PROCESO.value
    assert "No se cambió el estado del activo" in resultado.seguimiento[1].comentario
    assert "de 'Prestado' a 'En mantenimiento'" in resultado.seguimiento[1].comentario


async def test_si_el_activo_ya_esta_en_el_estado_destino_no_hace_nada(
    repositorio_mock, notificador_mock
):
    activo = _activo_estado("en_mantenimiento")
    service = _servicio(repositorio_mock, notificador_mock, activo)

    resultado = await service.ejecutar(
        _dto_estado(EstadoSolicitud.EN_PROCESO, "tecnico-1", "mantenimiento")
    )

    activo.cambiar_estado.assert_not_called()
    assert len(resultado.seguimiento) == 1


async def test_si_el_activo_ya_no_existe_la_solicitud_avanza_sin_nota(
    repositorio_mock, notificador_mock
):
    activo = _activo_estado(None)
    service = _servicio(repositorio_mock, notificador_mock, activo)

    resultado = await service.ejecutar(
        _dto_estado(EstadoSolicitud.EN_PROCESO, "tecnico-1", "mantenimiento")
    )

    activo.cambiar_estado.assert_not_called()
    assert len(resultado.seguimiento) == 1


async def test_si_falla_el_activo_la_solicitud_no_se_guarda(repositorio_mock, notificador_mock):
    activo = _activo_estado("disponible")
    activo.cambiar_estado.side_effect = RuntimeError("base de datos caida")
    service = _servicio(repositorio_mock, notificador_mock, activo)

    with pytest.raises(RuntimeError):
        await service.ejecutar(_dto_estado(EstadoSolicitud.EN_PROCESO, "tecnico-1", "mantenimiento"))

    repositorio_mock.guardar.assert_not_called()


async def test_una_solicitud_sin_permiso_no_llega_a_tocar_el_activo(repositorio_mock, notificador_mock):
    activo = _activo_estado("disponible")
    service = _servicio(repositorio_mock, notificador_mock, activo)

    with pytest.raises(SolicitudSinPermisoError):
        await service.ejecutar(_dto_estado(EstadoSolicitud.EN_PROCESO, "solicitante-1", "empleado"))

    activo.obtener_estado.assert_not_called()
    activo.cambiar_estado.assert_not_called()
