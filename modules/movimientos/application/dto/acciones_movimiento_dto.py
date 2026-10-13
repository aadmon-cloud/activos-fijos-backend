from dataclasses import dataclass, field


@dataclass
class ConfirmarSalidaDTO:
    id_movimiento: str
    actor_id: str
    actor_nombre: str

    # Activos que salen; None = todos los que esperan a administracion. Los demas se rechazan.
    activo_ids: list[str] | None = None
    motivo_no_incluidos: str | None = None


@dataclass
class SolicitarDevolucionDTO:
    id_movimiento: str
    actor_id: str
    actor_nombre: str
    actor_rol: str

    # Activos que devuelve; None = todos los que tiene.
    activo_ids: list[str] | None = None


@dataclass
class ReciboActivoDTO:
    """Como se recibe un activo de vuelta: bien, o con una novedad que se describe."""

    activo_id: str
    con_novedad: bool = False
    observacion: str | None = None


@dataclass
class ConfirmarDevolucionDTO:
    id_movimiento: str
    actor_id: str
    actor_nombre: str

    # Un recibo por cada activo que se recibe; None = todos los que estan fuera, sin novedad.
    recibos: list[ReciboActivoDTO] | None = field(default=None)
