from dataclasses import dataclass, fields

from modules.mantenimientos.application.dto.mantenimiento_dto import MantenimientoDTO
from modules.mantenimientos.application.ports.resolutor_nombres_port import (
    NombresReferenciasMantenimiento,
)
from modules.mantenimientos.domain.entities import EstadoMantenimiento
from modules.mantenimientos.domain.transiciones import estados_destino


@dataclass
class MantenimientoConNombresDTO(MantenimientoDTO):
    activo_nombre: str | None
    activo_numero_inventario: str | None
    tecnico_nombre: str | None

    # Estados a los que puede pasar ahora (quien ve un mantenimiento tambien puede gestionarlo).
    estados_permitidos: list[str]


@dataclass
class ListadoMantenimientosDTO:
    items: list[MantenimientoConNombresDTO]
    total: int
    skip: int
    limit: int


def mantenimiento_con_nombres_a_dto(
    mantenimiento: MantenimientoDTO, nombres: NombresReferenciasMantenimiento
) -> MantenimientoConNombresDTO:
    activo = nombres.activos.get(mantenimiento.activo_id)
    base = {campo.name: getattr(mantenimiento, campo.name) for campo in fields(MantenimientoDTO)}

    return MantenimientoConNombresDTO(
        **base,
        activo_nombre=activo.nombre if activo else None,
        activo_numero_inventario=activo.numero_inventario if activo else None,
        tecnico_nombre=nombres.tecnicos.get(mantenimiento.tecnico_responsable_id),
        estados_permitidos=[
            estado.value for estado in estados_destino(EstadoMantenimiento(mantenimiento.estado))
        ],
    )
