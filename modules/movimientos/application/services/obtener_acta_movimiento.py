from modules.movimientos.application.dto.chequeo_movimiento_dto import ObtenerActaDTO
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.domain.errors import ActaNoEncontradaError, MovimientoNoEncontradoError
from modules.movimientos.domain.permisos import puede_ver
from shared.application.file_storage.ports import AlmacenArchivosPort, ArchivoAlmacenado


class ObtenerActaMovimientoService:
    """El PDF de un acta, con la misma regla de visibilidad que el movimiento."""

    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        almacen_archivos: AlmacenArchivosPort,
        activo_movimiento: ActivoMovimientoPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._almacen_archivos = almacen_archivos
        self._activo_movimiento = activo_movimiento

    async def ejecutar(self, dto: ObtenerActaDTO) -> ArchivoAlmacenado:
        movimiento = await self._movimiento_repository.obtener_por_id(dto.id_movimiento)
        if movimiento is None:
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        resumenes = await self._activo_movimiento.obtener_resumenes(movimiento.activo_ids)
        responsables = {activo_id: resumen.responsable_id for activo_id, resumen in resumenes.items()}
        if not puede_ver(movimiento, dto.actor_id, dto.actor_rol, responsables):
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        acta = movimiento.acta(dto.acta_id)
        if acta is None or acta.archivo_id is None:
            raise ActaNoEncontradaError(dto.acta_id)

        archivo = await self._almacen_archivos.obtener(acta.archivo_id)
        if archivo is None:
            raise ActaNoEncontradaError(dto.acta_id)

        return archivo
