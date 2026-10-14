from collections.abc import Mapping
from dataclasses import dataclass, replace

from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO
from modules.movimientos.application.ports.resolutor_nombres_port import (
    NombresReferenciasMovimiento,
)


@dataclass
class ListadoMovimientosDTO:
    items: list[MovimientoDTO]
    total: int
    skip: int
    limit: int


def movimiento_con_nombres_a_dto(
    movimiento: MovimientoDTO,
    nombres: NombresReferenciasMovimiento,
    acciones_permitidas: list[str],
    acciones_por_activo: Mapping[str, list[str]],
    actas_aceptables: frozenset[str] = frozenset(),
) -> MovimientoDTO:
    """Completa un movimiento con los nombres vigentes y con lo que el usuario puede hacer (en total y por activo).

    `actas_aceptables`: ids de las actas que el usuario con sesion puede aceptar."""
    items = []
    for item in movimiento.items:
        activo = nombres.activos.get(item.activo_id)
        items.append(
            replace(
                item,
                activo_nombre=activo.nombre if activo else None,
                activo_numero_inventario=activo.numero_inventario if activo else None,
                responsable_original_nombre=(
                    nombres.usuarios.get(item.responsable_original_id)
                    if item.responsable_original_id
                    else None
                ),
                acciones_permitidas=acciones_por_activo.get(item.activo_id, []),
            )
        )

    actas = []
    for acta in movimiento.actas:
        lineas = []
        for linea in acta.lineas:
            activo = nombres.activos.get(linea.activo_id)
            lineas.append(
                replace(
                    linea,
                    activo_nombre=activo.nombre if activo else None,
                    activo_numero_inventario=activo.numero_inventario if activo else None,
                )
            )
        actas.append(replace(acta, lineas=lineas, puede_aceptar=acta.id in actas_aceptables))

    return replace(
        movimiento,
        items=items,
        actas=actas,
        usuario_destino_nombre=(
            nombres.usuarios.get(movimiento.usuario_destino_id) if movimiento.usuario_destino_id else None
        ),
        acciones_permitidas=acciones_permitidas,
    )
