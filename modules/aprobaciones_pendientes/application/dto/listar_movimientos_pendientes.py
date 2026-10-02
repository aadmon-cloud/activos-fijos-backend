from pydantic import BaseModel, Field

from modules.aprobaciones_pendientes.domain.entities.movimiento_pendiente import (
    EstadoMovimientoPendiente,
    TipoPropuesto,
)


class ListarMovimientosPendientesInput(BaseModel):
    estado: EstadoMovimientoPendiente | None = None
    tipo_propuesto: TipoPropuesto | None = None
    creado_por_id: str | None = None
    """Forzado por el servicio según el rol de quien consulta — no lo fija
    directamente el request HTTP (ver `ListarMovimientosPendientesService`)."""
    pagina: int = Field(default=1, ge=1)
    limite: int = Field(default=20, ge=1, le=200)
