from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.solicitudes.application.dto.listar_solicitudes_dto import ListarSolicitudesDTO
from modules.solicitudes.application.ports.resolutor_referencias import (
    ActivoNombre,
    NombresReferenciasSolicitud,
)
from modules.solicitudes.application.ports.solicitud_repository import VisibilidadSolicitud
from modules.solicitudes.application.services.listar_solicitudes import ListarSolicitudesService
from modules.solicitudes.domain.entities import (
    EstadoSolicitud,
    PrioridadSolicitud,
    Solicitud,
    TipoSolicitud,
)
from shared.domain.entities.audit import AuditPersona


def _solicitud(id_: str, area_id: str | None = None) -> Solicitud:
    return Solicitud(
        id=id_,
        tipo=TipoSolicitud.MANTENIMIENTO,
        activo_id="a1",
        descripcion="desc",
        prioridad=PrioridadSolicitud.MEDIA,
        evidencias=[],
        estado=EstadoSolicitud.PENDIENTE,
        rol_asignado="mantenimiento" if area_id is None else None,
        area_id=area_id,
        seguimiento=[],
        creado_por=AuditPersona(id_persona="u9", nombre="Ana Gomez", fecha=datetime(2026, 5, 1, tzinfo=UTC)),
        actualizado_por=None,
    )


def _repositorio(solicitudes, total=None):
    mock = AsyncMock()
    mock.listar.return_value = solicitudes
    mock.contar.return_value = len(solicitudes) if total is None else total
    return mock


def _resolutor():
    mock = AsyncMock()
    mock.resolver.return_value = NombresReferenciasSolicitud(
        activos={"a1": ActivoNombre(nombre="Laptop", numero_inventario="INV-001")},
        areas={"ar1": "Tecnologia"},
    )
    return mock


def _dto(**kwargs) -> ListarSolicitudesDTO:
    valores = dict(actor_id="u1", actor_rol="empleado", actor_area_id=None)
    valores.update(kwargs)
    return ListarSolicitudesDTO(**valores)


async def test_listar_retorna_items_con_nombres_total_y_datos_de_creacion():
    service = ListarSolicitudesService(
        _repositorio([_solicitud("1"), _solicitud("2", "ar1")], total=40), _resolutor()
    )

    resultado = await service.ejecutar(_dto(skip=10, limit=2))

    assert resultado.total == 40
    assert (resultado.skip, resultado.limit) == (10, 2)
    primero, segundo = resultado.items
    assert primero.activo_nombre == "Laptop"
    assert primero.activo_numero_inventario == "INV-001"
    assert primero.area_nombre is None
    assert primero.creado_por_nombre == "Ana Gomez"
    assert primero.fecha_creacion == datetime(2026, 5, 1, tzinfo=UTC)
    assert segundo.area_nombre == "Tecnologia"


async def test_un_usuario_normal_solo_ve_lo_suyo_el_filtro_de_visibilidad_se_aplica_a_listar_y_contar():
    repositorio = _repositorio([])
    service = ListarSolicitudesService(repositorio, _resolutor())

    await service.ejecutar(_dto(actor_id="u1", actor_rol="mantenimiento", actor_area_id="ar1"))

    esperado = VisibilidadSolicitud(actor_id="u1", rol="mantenimiento", area_id="ar1")
    assert repositorio.listar.call_args.kwargs["visible_para"] == esperado
    assert repositorio.contar.call_args.kwargs["visible_para"] == esperado


async def test_el_administrador_general_ve_todo_sin_restriccion_de_visibilidad():
    repositorio = _repositorio([])
    service = ListarSolicitudesService(repositorio, _resolutor())

    await service.ejecutar(_dto(actor_rol="administrador_general"))

    assert repositorio.listar.call_args.kwargs["visible_para"] is None
    assert repositorio.contar.call_args.kwargs["visible_para"] is None


async def test_los_filtros_del_usuario_se_combinan_con_la_visibilidad_y_van_igual_a_contar():
    repositorio = _repositorio([])
    service = ListarSolicitudesService(repositorio, _resolutor())

    await service.ejecutar(
        _dto(tipo=TipoSolicitud.CAMBIO, estado=EstadoSolicitud.PENDIENTE, creado_por_id="u1")
    )

    for llamada in (repositorio.listar, repositorio.contar):
        assert llamada.call_args.kwargs["tipo"] == TipoSolicitud.CAMBIO
        assert llamada.call_args.kwargs["estado"] == EstadoSolicitud.PENDIENTE
        assert llamada.call_args.kwargs["creado_por_id"] == "u1"
        assert llamada.call_args.kwargs["visible_para"] is not None


async def test_listar_limita_el_limit_maximo():
    repositorio = _repositorio([])
    service = ListarSolicitudesService(repositorio, _resolutor())

    resultado = await service.ejecutar(_dto(limit=5000))

    assert repositorio.listar.call_args.kwargs["limit"] == 1000
    assert resultado.limit == 1000


async def test_listar_sin_resultados_no_consulta_nombres():
    resolutor = _resolutor()
    service = ListarSolicitudesService(_repositorio([]), resolutor)

    resultado = await service.ejecutar(_dto())

    assert resultado.items == []
    resolutor.resolver.assert_not_called()


async def test_un_activo_que_ya_no_existe_queda_con_nombre_none():
    resolutor = AsyncMock()
    resolutor.resolver.return_value = NombresReferenciasSolicitud()
    service = ListarSolicitudesService(_repositorio([_solicitud("1")]), resolutor)

    resultado = await service.ejecutar(_dto())

    assert resultado.items[0].activo_nombre is None
    assert resultado.items[0].activo_numero_inventario is None
