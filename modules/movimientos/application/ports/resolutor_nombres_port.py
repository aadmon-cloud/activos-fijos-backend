from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ReferenciasMovimiento:
    activo_ids: set[str] = field(default_factory=set)

    # Usuarios cuyo nombre se necesita: destinatarios, responsables originales y quienes decidieron.
    usuario_ids: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class ActivoNombreMovimiento:
    nombre: str
    numero_inventario: str

    # Responsable actual del activo (no el original del movimiento): define quien puede ver y decidir.
    responsable_id: str | None = None


@dataclass(frozen=True)
class NombresReferenciasMovimiento:
    """Nombres vigentes de las referencias; un id ausente significa que ya no existe."""

    activos: dict[str, ActivoNombreMovimiento] = field(default_factory=dict)
    usuarios: dict[str, str] = field(default_factory=dict)

    def responsables_actuales(self) -> dict[str, str | None]:
        return {activo_id: activo.responsable_id for activo_id, activo in self.activos.items()}


class ResolutorNombresMovimientoPort(ABC):
    @abstractmethod
    async def resolver(
        self, referencias: ReferenciasMovimiento
    ) -> NombresReferenciasMovimiento: ...
