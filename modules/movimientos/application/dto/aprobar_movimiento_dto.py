from dataclasses import dataclass


@dataclass
class AprobarMovimientoDTO:
    id_movimiento: str
    actor_id: str
    actor_nombre: str
    actor_rol: str

    # Activos sobre los que decide; None = todos los que este usuario puede decidir.
    activo_ids: list[str] | None = None
