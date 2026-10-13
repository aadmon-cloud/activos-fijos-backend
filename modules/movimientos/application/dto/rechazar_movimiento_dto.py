from dataclasses import dataclass


@dataclass
class RechazarMovimientoDTO:
    id_movimiento: str
    motivo_rechazo: str
    actor_id: str
    actor_nombre: str
    actor_rol: str

    # Activos que rechaza; None = todos los que este usuario puede decidir.
    activo_ids: list[str] | None = None
