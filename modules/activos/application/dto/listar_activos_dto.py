from dataclasses import dataclass

from modules.activos.domain.entities import EstadoCicloVida


@dataclass
class ListarActivosDTO:
    area_id: str | None = None
    categoria_id: str | None = None
    responsable_id: str | None = None
    condicion_id: str | None = None
    sede_id: str | None = None
    lugar_id: str | None = None
    estado_ciclo_vida: EstadoCicloVida | None = None
    busqueda: str | None = None
    skip: int = 0
    limit: int = 100
