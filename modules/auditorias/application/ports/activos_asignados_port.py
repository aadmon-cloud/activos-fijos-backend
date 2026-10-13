from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class ActivoAsignado:
    id: str
    nombre: str
    numero_inventario: str
    tipo: str
    descripcion: str | None
    serie: str | None
    estado_ciclo_vida: str


class ActivosAsignadosPort(ABC):
    @abstractmethod
    async def listar_por_responsable(self, usuario_id: str) -> list[ActivoAsignado]: ...
