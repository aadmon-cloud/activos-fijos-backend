from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReferenciasSolicitud:
    activo_ids: set[str] = field(default_factory=set)
    area_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class ActivoNombre:
    nombre: str
    numero_inventario: str


@dataclass(frozen=True)
class NombresReferenciasSolicitud:
    """Nombres vigentes de las referencias; un id ausente significa que ya no existe."""

    activos: dict[str, ActivoNombre] = field(default_factory=dict)
    areas: dict[str, str] = field(default_factory=dict)


class ResolutorReferenciasPort(ABC):
    @abstractmethod
    async def resolver(self, referencias: ReferenciasSolicitud) -> NombresReferenciasSolicitud: ...
