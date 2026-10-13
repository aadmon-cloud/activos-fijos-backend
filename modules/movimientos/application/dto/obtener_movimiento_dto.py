from dataclasses import dataclass


@dataclass
class ObtenerMovimientoDTO:
    """Compartido por obtener movimiento y obtener comprobante: ambos dependen de quien consulta."""

    id_movimiento: str
    actor_id: str
    actor_rol: str
