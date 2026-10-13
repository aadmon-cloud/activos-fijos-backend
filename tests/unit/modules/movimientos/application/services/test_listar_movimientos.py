from unittest.mock import AsyncMock

from modules.movimientos.application.dto.listar_movimientos_dto import ListarMovimientosDTO
from modules.movimientos.application.ports.movimiento_repository import (
    ParaMiMovimiento,
    VisibilidadMovimiento,
)
from modules.movimientos.application.ports.resolutor_nombres_port import (
    ActivoNombreMovimiento,
    NombresReferenciasMovimiento,
)
from modules.movimientos.application.services.listar_movimientos import ListarMovimientosService
from modules.movimientos.domain.entities import EstadoItemMovimiento as I
from modules.movimientos.domain.entities import EstadoMovimiento as E


def _dto(actor_id="u1", rol="empleado", **overrides) -> ListarMovimientosDTO:
    return ListarMovimientosDTO(actor_id=actor_id, actor_rol=rol, **overrides)


def _servicio(movimientos, total=None, ids_a_cargo=("a1",)):
    repo = AsyncMock()
    repo.listar.return_value = movimientos
    repo.contar.return_value = len(movimientos) if total is None else total
    resolutor = AsyncMock()
    resolutor.resolver.return_value = NombresReferenciasMovimiento(
        activos={
            "a1": ActivoNombreMovimiento("Proyector", "INV-1", responsable_id="u1"),
            "a2": ActivoNombreMovimiento("Pantalla", "INV-2", responsable_id="u3"),
        },
        usuarios={"u1": "Ana Uno", "u2": "Luis Dos", "u3": "Eva Tres"},
    )
    activo_movimiento = AsyncMock()
    activo_movimiento.listar_ids_por_responsable.return_value = list(ids_a_cargo)

    return ListarMovimientosService(repo, resolutor, activo_movimiento), repo, activo_movimiento


async def test_el_administrador_lista_todo_sin_restriccion_de_visibilidad(fabrica):
    service, repo, activo_movimiento = _servicio([fabrica.movimiento()])

    await service.ejecutar(_dto("u7", "administrador_general"))

    assert repo.listar.await_args.kwargs["visible_para"] is None
    activo_movimiento.listar_ids_por_responsable.assert_not_called()


async def test_un_usuario_solo_ve_lo_que_tiene_que_ver_con_el(fabrica):
    service, repo, _ = _servicio([fabrica.movimiento()], ids_a_cargo=("a1", "a5"))

    await service.ejecutar(_dto("u1"))

    assert repo.listar.await_args.kwargs["visible_para"] == VisibilidadMovimiento("u1", frozenset({"a1", "a5"}))
    assert repo.contar.await_args.kwargs["visible_para"] == VisibilidadMovimiento("u1", frozenset({"a1", "a5"}))


async def test_para_mi_filtra_por_responsable_o_destinatario(fabrica):
    service, repo, _ = _servicio([fabrica.movimiento()])

    await service.ejecutar(_dto("u1", para_mi=True))

    assert repo.listar.await_args.kwargs["para_mi"] == ParaMiMovimiento("u1", frozenset({"a1"}), False)


async def test_para_mi_del_administrador_incluye_lo_que_espera_su_accion(fabrica):
    service, repo, activo_movimiento = _servicio([fabrica.movimiento()], ids_a_cargo=("a9",))

    await service.ejecutar(_dto("u7", "administrador_general", para_mi=True))

    assert repo.listar.await_args.kwargs["para_mi"] == ParaMiMovimiento("u7", frozenset({"a9"}), True)
    assert repo.listar.await_args.kwargs["visible_para"] is None


async def test_sin_para_mi_no_se_filtra_por_concierne(fabrica):
    service, repo, _ = _servicio([fabrica.movimiento()])

    await service.ejecutar(_dto("u1"))

    assert repo.listar.await_args.kwargs["para_mi"] is None


async def test_pasa_los_filtros_y_acota_el_limite(fabrica):
    service, repo, _ = _servicio([])

    resultado = await service.ejecutar(_dto("u7", "administrador_general", activo_id="a1", limit=99999, skip=5))

    assert repo.listar.await_args.kwargs["activo_id"] == "a1"
    assert repo.listar.await_args.kwargs["limit"] == 1000
    assert resultado.items == [] and resultado.limit == 1000 and resultado.skip == 5


async def test_incluye_nombres_y_acciones_por_activo_y_del_movimiento(fabrica):
    movimiento = fabrica.movimiento(
        usuario_destino_id="u2",
        items=[
            fabrica.item(activo_id="a1", responsable_original_id="u1", estado=I.PENDIENTE_RESPONSABLE),
            fabrica.item(activo_id="a2", responsable_original_id="u3", estado=I.PENDIENTE_RESPONSABLE),
        ],
    )
    service, _, _ = _servicio([movimiento])

    resultado = await service.ejecutar(_dto("u1"))

    dto = resultado.items[0]
    assert resultado.total == 1
    assert dto.usuario_destino_nombre == "Luis Dos"
    assert [i.activo_nombre for i in dto.items] == ["Proyector", "Pantalla"]
    assert dto.items[0].responsable_original_nombre == "Ana Uno"
    assert dto.items[0].acciones_permitidas == ["aprobar", "rechazar"]
    assert dto.items[1].acciones_permitidas == []
    assert dto.acciones_permitidas == ["aprobar", "rechazar"]


async def test_el_administrador_ve_confirmar_salida_en_lo_que_espera_a_administracion(fabrica):
    movimiento = fabrica.movimiento(
        estado=E.APROBADO_RESPONSABLE, items=[fabrica.item(activo_id="a1", estado=I.PENDIENTE_ADMIN)]
    )
    service, _, _ = _servicio([movimiento])

    resultado = await service.ejecutar(_dto("u7", "administrador_general"))

    assert resultado.items[0].acciones_permitidas == ["confirmar_salida", "rechazar"]
