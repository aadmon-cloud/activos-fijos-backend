from dataclasses import dataclass


@dataclass
class ActorMovimientoDTO:
    """Compartido por confirmar-salida, confirmar-devolucion y ejecutar-baja: las 3 acciones son
    siempre administrativas y solo necesitan el id del movimiento y quien ejecuta la accion."""

    id_movimiento: str
    actor_id: str
    actor_nombre: str
