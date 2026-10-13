from dataclasses import dataclass

from modules.movimientos.domain.entities import EstadoMovimiento, TipoMovimiento


@dataclass
class ListarMovimientosDTO:
    actor_id: str
    actor_rol: str
    tipo: TipoMovimiento | None = None
    estado: EstadoMovimiento | None = None
    activo_id: str | None = None
    usuario_destino_id: str | None = None
    creado_por_id: str | None = None

    # Solo lo que le concierne como responsable o destinatario (y, al administrador, lo que espera su accion).
    para_mi: bool = False
    skip: int = 0
    limit: int = 100
