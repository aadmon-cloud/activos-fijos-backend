from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReferenciasActivo:
    """Ids referenciados por un conjunto de activos, agrupados por catalogo."""

    categoria_ids: set[str] = field(default_factory=set)
    area_ids: set[str] = field(default_factory=set)
    responsable_ids: set[str] = field(default_factory=set)
    condicion_ids: set[str] = field(default_factory=set)
    sede_ids: set[str] = field(default_factory=set)
    lugar_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class CondicionResuelta:
    nombre: str
    color: str


@dataclass(frozen=True)
class NombresReferencias:
    """Nombres vigentes de las referencias; un id ausente significa que ya no existe."""

    categorias: dict[str, str] = field(default_factory=dict)
    areas: dict[str, str] = field(default_factory=dict)
    responsables: dict[str, str] = field(default_factory=dict)
    condiciones: dict[str, CondicionResuelta] = field(default_factory=dict)
    sedes: dict[str, str] = field(default_factory=dict)
    lugares: dict[str, str] = field(default_factory=dict)


class ResolutorNombresPort(ABC):
    @abstractmethod
    async def resolver(self, referencias: ReferenciasActivo) -> NombresReferencias: ...
