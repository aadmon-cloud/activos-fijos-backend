"""Piezas comunes de los casos de uso que actuan sobre varios activos de un movimiento."""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Callable

from modules.movimientos.application.ports.activo_movimiento_port import (
    ActivoMovimientoPort,
    ActivoResumenMovimiento,
)
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.domain.entities import ItemMovimiento, Movimiento
from modules.movimientos.domain.errors import (
    ActivoNoPerteneceAlMovimientoError,
    MovimientoNoEncontradoError,
    SinActivosParaProcesarError,
)
from modules.movimientos.domain.permisos import AccionMovimiento, acciones_de_item, puede_ver
from shared.domain.entities.audit import AuditPersona


def ahora_audit(actor_id: str, actor_nombre: str) -> AuditPersona:
    return AuditPersona(id_persona=actor_id, nombre=actor_nombre, fecha=datetime.now(UTC))


async def cargar_movimiento_visible(
    movimiento_repository: MovimientoRepositoryPort,
    activo_movimiento: ActivoMovimientoPort,
    id_movimiento: str,
    actor_id: str,
    actor_rol: str,
) -> tuple[Movimiento, dict[str, ActivoResumenMovimiento]]:
    """El movimiento y el resumen vigente de sus activos. Sin acceso se responde como si no existiera."""
    movimiento = await movimiento_repository.obtener_por_id(id_movimiento)
    if movimiento is None:
        raise MovimientoNoEncontradoError(id_movimiento)

    resumenes = await activo_movimiento.obtener_resumenes(movimiento.activo_ids)
    responsables = {activo_id: resumen.responsable_id for activo_id, resumen in resumenes.items()}
    if not puede_ver(movimiento, actor_id, actor_rol, responsables):
        raise MovimientoNoEncontradoError(id_movimiento)

    return movimiento, resumenes


def items_con_accion(
    movimiento: Movimiento,
    resumenes: dict[str, ActivoResumenMovimiento],
    actor_id: str,
    actor_rol: str,
    accion: AccionMovimiento,
) -> list[ItemMovimiento]:
    """Los activos del movimiento sobre los que este usuario puede ejecutar la accion."""
    elegibles = []
    for item in movimiento.items:
        resumen = resumenes.get(item.activo_id)
        responsable = resumen.responsable_id if resumen else None
        if accion in acciones_de_item(movimiento, item, actor_id, actor_rol, responsable):
            elegibles.append(item)

    return elegibles


def elegir_activos(
    movimiento: Movimiento,
    elegibles: list[ItemMovimiento],
    activo_ids: list[str] | None,
    error_sin_elegibles: Exception,
) -> list[ItemMovimiento]:
    """Activos sobre los que se actua: los pedidos (deben hacer parte del movimiento y poderse procesar) o,
    si no se pidio ninguno en particular, todos los elegibles."""
    if activo_ids is None:
        if not elegibles:
            raise error_sin_elegibles

        return elegibles

    pedidos = list(dict.fromkeys(activo_ids))
    if not pedidos:
        raise SinActivosParaProcesarError()

    ids_elegibles = {item.activo_id for item in elegibles}
    for activo_id in pedidos:
        if movimiento.item(activo_id) is None:
            raise ActivoNoPerteneceAlMovimientoError(activo_id)
        if activo_id not in ids_elegibles:
            raise error_sin_elegibles

    return [item for item in elegibles if item.activo_id in set(pedidos)]


def reemplazar_items(
    movimiento: Movimiento, cambios: dict[str, ItemMovimiento]
) -> list[ItemMovimiento]:
    """Los items del movimiento con los modificados puestos en su lugar (conserva el orden)."""
    return [cambios.get(item.activo_id, item) for item in movimiento.items]


def con_cambios(item: ItemMovimiento, **cambios) -> ItemMovimiento:
    return replace(item, **cambios)


async def aplicar_a_activos(
    items: list[ItemMovimiento],
    aplicar: Callable,
    deshacer: Callable,
    error: Callable[[str], Exception],
) -> None:
    """Aplica un cambio a cada activo; si alguno falla, deshace los ya aplicados y lanza el error.

    Los cambios sobre activos no son transaccionales: sin esto una falla a mitad dejaria unos activos
    cambiados y otros no, con el movimiento sin actualizar.
    """
    aplicados: list[ItemMovimiento] = []

    for item in items:
        if not await aplicar(item):
            for hecho in reversed(aplicados):
                await deshacer(hecho)
            raise error(item.activo_id)
        aplicados.append(item)
