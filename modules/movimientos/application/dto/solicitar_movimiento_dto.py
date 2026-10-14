from dataclasses import dataclass
from datetime import datetime

from modules.movimientos.domain.entities import SentidoPrestamo, TipoMovimiento


@dataclass
class SolicitarMovimientoDTO:
    tipo: TipoMovimiento
    activo_ids: list[str]
    descripcion: str
    solicitante_id: str
    solicitante_nombre: str
    solicitante_rol: str
    sentido: SentidoPrestamo | None = None
    usuario_destino_id: str | None = None
    evento_nombre: str | None = None
    fecha_salida_estimada: datetime | None = None
    fecha_retorno_estimada: datetime | None = None

    # Lo que la matriz de permisos le deja hacer a quien solicita. Si no se informa (None) se deduce del rol:
    # solo el administrador pide bajas y elige a otra persona como destinatario.
    puede_solicitar_baja: bool | None = None
    puede_elegir_destinatario: bool | None = None
