from modules.movimientos.application.dto.obtener_movimiento_dto import ObtenerMovimientoDTO
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.domain.errors import (
    ComprobanteNoDisponibleError,
    MovimientoNoEncontradoError,
)
from modules.movimientos.domain.permisos import puede_ver
from shared.application.file_storage.ports import AlmacenArchivosPort, ArchivoAlmacenado


class ObtenerComprobanteMovimientoService:
    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        almacen_archivos: AlmacenArchivosPort,
        activo_movimiento: ActivoMovimientoPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._almacen_archivos = almacen_archivos
        self._activo_movimiento = activo_movimiento

    async def ejecutar(self, dto: ObtenerMovimientoDTO) -> ArchivoAlmacenado:
        movimiento = await self._movimiento_repository.obtener_por_id(dto.id_movimiento)
        if movimiento is None:
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        resumenes = await self._activo_movimiento.obtener_resumenes(movimiento.activo_ids)
        responsables = {activo_id: resumen.responsable_id for activo_id, resumen in resumenes.items()}

        # El comprobante sigue la misma regla de visibilidad que el movimiento.
        if not puede_ver(movimiento, dto.actor_id, dto.actor_rol, responsables):
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        if movimiento.comprobante_archivo_id is None:
            raise ComprobanteNoDisponibleError(dto.id_movimiento)

        archivo = await self._almacen_archivos.obtener(movimiento.comprobante_archivo_id)
        if archivo is None:
            raise ComprobanteNoDisponibleError(dto.id_movimiento)
        return archivo
