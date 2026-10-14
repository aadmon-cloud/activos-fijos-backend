from dataclasses import dataclass


@dataclass
class ConfirmarSalidaDTO:
    """Cierra el chequeo de salida: sale lo chequeado como encontrado (o con novedad); lo demas se rechaza."""

    id_movimiento: str
    actor_id: str
    actor_nombre: str
    actor_correo: str

    # Motivo para los activos que no salen y no tienen observacion propia en su chequeo.
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
class ConfirmarDevolucionDTO:
    """Cierra el chequeo de ingreso: se reciben los chequeados como encontrados (o con novedad)."""

    id_movimiento: str
    actor_id: str
    actor_nombre: str
    actor_correo: str
