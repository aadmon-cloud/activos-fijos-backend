from datetime import UTC, datetime
from unittest.mock import AsyncMock

from modules.mantenimientos.application.dto.listar_mantenimientos_dto import (
    ListarMantenimientosDTO,
)
from modules.mantenimientos.application.ports.resolutor_nombres_port import (
    ActivoNombre,
    NombresReferenciasMantenimiento,
)
from modules.mantenimientos.application.services.listar_mantenimientos import (
    ListarMantenimientosService,
)
from modules.mantenimientos.domain.entities import EstadoMantenimiento, Mantenimiento, TipoMantenimiento
from shared.domain.entities.audit import AuditPersona

_AUDIT = AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC))


def _mantenimiento(id_: str) -> Mantenimiento:
    return Mantenimiento(
        id=id_,
        activo_id="a1",
        solicitud_id=None,
        tipo=TipoMantenimiento.PREVENTIVO,
        tecnico_responsable_id="u1",
        fecha=datetime.now(UTC),
        observaciones=None,
        costo=None,
        documentos=[],
        evidencias=[],
        estado=EstadoMantenimiento.PROGRAMADO,
        frecuencia_dias=None,
        proxima_fecha_sugerida=None,
        alerta_enviada=False,
        creado_por=_AUDIT,
        actualizado_por=None,
    )


def _repositorio(items, total=None):
    mock = AsyncMock()
    mock.listar.return_value = items
    mock.contar.return_value = len(items) if total is None else total
    return mock


def _resolutor():
    mock = AsyncMock()
    mock.resolver.return_value = NombresReferenciasMantenimiento(
        activos={"a1": ActivoNombre(nombre="Laptop", numero_inventario="INV-001")},
        tecnicos={"u1": "Juan Perez"},
    )
    return mock


async def test_listar_retorna_items_con_nombres_y_total():
    service = ListarMantenimientosService(
        _repositorio([_mantenimiento("1")], total=5), _resolutor()
    )

    resultado = await service.ejecutar(ListarMantenimientosDTO())

    assert resultado.total == 5
    assert resultado.items[0].activo_nombre == "Laptop"
    assert resultado.items[0].tecnico_nombre == "Juan Perez"


async def test_listar_limita_el_limit_maximo():
    repositorio = _repositorio([])
    service = ListarMantenimientosService(repositorio, _resolutor())

    await service.ejecutar(ListarMantenimientosDTO(limit=5000))

    assert repositorio.listar.call_args.kwargs["limit"] == 1000


async def test_listar_sin_resultados_no_consulta_nombres():
    resolutor = _resolutor()
    service = ListarMantenimientosService(_repositorio([]), resolutor)

    resultado = await service.ejecutar(ListarMantenimientosDTO())

    assert resultado.items == []
    resolutor.resolver.assert_not_called()


async def test_un_activo_que_ya_no_existe_queda_con_nombre_none():
    resolutor = AsyncMock()
    resolutor.resolver.return_value = NombresReferenciasMantenimiento()
    service = ListarMantenimientosService(_repositorio([_mantenimiento("1")]), resolutor)

    resultado = await service.ejecutar(ListarMantenimientosDTO())

    assert resultado.items[0].activo_nombre is None
    assert resultado.items[0].tecnico_nombre is None
