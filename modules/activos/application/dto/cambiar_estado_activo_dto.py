from dataclasses import dataclass

from modules.activos.domain.entities import EstadoCicloVida


@dataclass
class CambiarEstadoActivoDTO:
    id_activo: str
    estado_nuevo: EstadoCicloVida
    actualizado_por_id: str
    actualizado_por_nombre: str
