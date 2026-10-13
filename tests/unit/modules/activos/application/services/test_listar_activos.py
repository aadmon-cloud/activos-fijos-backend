from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock

from modules.activos.application.dto.listar_activos_dto import ListarActivosDTO
from modules.activos.application.ports.resolutor_nombres import (
    CondicionResuelta,
    NombresReferencias,
)
from modules.activos.application.services.listar_activos import ListarActivosService
from modules.activos.domain.entities import Activo, EstadoCicloVida, TipoActivo
from shared.domain.entities.audit import AuditPersona


def _activo(id_: str) -> Activo:
    return Activo(
        id=id_,
        nombre="Laptop",
        numero_inventario=f"INV-{id_}",
        tipo=TipoActivo.ACTIVO_FIJO,
        marca=None,
        modelo=None,
        serie=None,
        descripcion=None,
        categoria_id="c1",
        area_id="a1",
        responsable_id="u1",
        condicion_id="cond1",
        estado_ciclo_vida=EstadoCicloVida.DISPONIBLE,
        sede_id="s1",
        lugar_id="l1",
        complementos=[],
        observaciones=None,
        foto_url=None,
        ficha_tecnica_url=None,
        creado_por=AuditPersona(id_persona="0", nombre="S", fecha=datetime.now(UTC)),
        actualizado_por=None,
    )


def _resolutor() -> AsyncMock:
    resolutor = AsyncMock()
    resolutor.resolver.return_value = NombresReferencias(
        categorias={"c1": "Computo"},
        areas={"a1": "Tecnologia"},
        responsables={"u1": "Ana Gomez"},
        condiciones={"cond1": CondicionResuelta(nombre="Bueno", color="#4CAF50")},
        sedes={"s1": "Prado"},
        lugares={"l1": "BANO1"},
    )

    return resolutor


def _repositorio(activos: list[Activo], total: int | None = None) -> AsyncMock:
    repositorio = AsyncMock()
    repositorio.listar.return_value = activos
    repositorio.contar.return_value = len(activos) if total is None else total

    return repositorio


async def test_listar_activos_retorna_items_con_nombres_y_total():
    service = ListarActivosService(_repositorio([_activo("1"), _activo("2")], total=57), _resolutor())

    resultado = await service.ejecutar(ListarActivosDTO(skip=10, limit=2))

    assert len(resultado.items) == 2
    assert resultado.total == 57
    assert (resultado.skip, resultado.limit) == (10, 2)
    assert resultado.items[0].responsable_nombre == "Ana Gomez"
    assert resultado.items[0].condicion_color == "#4CAF50"
    assert resultado.items[0].lugar_nombre == "BANO1"


async def test_listar_activos_resuelve_los_nombres_en_una_sola_consulta_con_ids_unicos():
    resolutor = _resolutor()
    service = ListarActivosService(_repositorio([_activo("1"), _activo("2")]), resolutor)

    await service.ejecutar(ListarActivosDTO())

    resolutor.resolver.assert_awaited_once()
    referencias = resolutor.resolver.call_args.args[0]
    assert referencias.categoria_ids == {"c1"}
    assert referencias.responsable_ids == {"u1"}


async def test_listar_activos_sin_resultados_no_consulta_nombres():
    resolutor = _resolutor()
    service = ListarActivosService(_repositorio([]), resolutor)

    resultado = await service.ejecutar(ListarActivosDTO())

    assert resultado.items == []
    assert resultado.total == 0
    resolutor.resolver.assert_not_called()


async def test_listar_activos_un_id_que_ya_no_existe_queda_con_nombre_none():
    resolutor = AsyncMock()
    resolutor.resolver.return_value = NombresReferencias()
    service = ListarActivosService(_repositorio([_activo("1")]), resolutor)

    resultado = await service.ejecutar(ListarActivosDTO())

    assert resultado.items[0].categoria_nombre is None
    assert resultado.items[0].condicion_nombre is None
    assert resultado.items[0].condicion_color is None


async def test_listar_activos_limita_el_limit_maximo_y_usa_los_mismos_filtros_para_contar():
    repositorio = _repositorio([])
    service = ListarActivosService(repositorio, _resolutor())

    resultado = await service.ejecutar(ListarActivosDTO(limit=5000, area_id="a1", busqueda="lap"))

    _, kwargs = repositorio.listar.call_args
    assert kwargs["limit"] == 1000
    assert resultado.limit == 1000
    _, kwargs_contar = repositorio.contar.call_args
    assert kwargs_contar["area_id"] == "a1"
    assert kwargs_contar["busqueda"] == "lap"
    assert "skip" not in kwargs_contar and "limit" not in kwargs_contar
