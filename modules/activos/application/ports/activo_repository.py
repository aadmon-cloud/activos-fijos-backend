from abc import ABC, abstractmethod

from modules.activos.domain.entities import Activo, EstadoCicloVida


class ActivoRepositoryPort(ABC):
    @abstractmethod
    async def guardar(self, activo: Activo) -> Activo: ...

    @abstractmethod
    async def obtener_por_id(self, id_activo: str) -> Activo | None: ...

    @abstractmethod
    async def obtener_por_numero_inventario(self, numero_inventario: str) -> Activo | None: ...

    @abstractmethod
    async def listar(
        self,
        area_id: str | None,
        categoria_id: str | None,
        responsable_id: str | None,
        condicion_id: str | None,
        sede_id: str | None,
        lugar_id: str | None,
        estado_ciclo_vida: EstadoCicloVida | None,
        busqueda: str | None,
        skip: int,
        limit: int,
    ) -> list[Activo]: ...
