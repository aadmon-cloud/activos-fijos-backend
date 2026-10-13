from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReferenciasMantenimiento:
    activo_ids: set[str] = field(default_factory=set)
    tecnico_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class ActivoNombre:
    nombre: str
    numero_inventario: str


@dataclass(frozen=True)
class NombresReferenciasMantenimiento:
    """Nombres vigentes de las referencias; un id ausente significa que ya no existe."""

    activos: dict[str, ActivoNombre] = field(default_factory=dict)
    tecnicos: dict[str, str] = field(default_factory=dict)


class ResolutorNombresMantenimientoPort(ABC):
    @abstractmethod
    async def resolver(
        self, referencias: ReferenciasMantenimiento
    ) -> NombresReferenciasMantenimiento: ...
