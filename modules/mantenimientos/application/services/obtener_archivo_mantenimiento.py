from modules.mantenimientos.application.ports.mantenimiento_repository import (
    MantenimientoRepositoryPort,
)
from modules.mantenimientos.domain.errors import (
    ArchivoNoEncontradoError,
    MantenimientoNoEncontradoError,
)
from shared.application.file_storage.ports import AlmacenArchivosPort, ArchivoAlmacenado


class ObtenerArchivoMantenimientoService:
    def __init__(
        self,
        mantenimiento_repository: MantenimientoRepositoryPort,
        almacen_archivos: AlmacenArchivosPort,
    ):
        self._mantenimiento_repository = mantenimiento_repository
        self._almacen_archivos = almacen_archivos

    async def ejecutar(self, id_mantenimiento: str, archivo_id: str) -> ArchivoAlmacenado:
        mantenimiento = await self._mantenimiento_repository.obtener_por_id(id_mantenimiento)
        if mantenimiento is None:
            raise MantenimientoNoEncontradoError(id_mantenimiento)

        ids_validos = {a.archivo_id for a in (*mantenimiento.documentos, *mantenimiento.evidencias)}
        if archivo_id not in ids_validos:
            raise ArchivoNoEncontradoError(archivo_id)

        archivo = await self._almacen_archivos.obtener(archivo_id)
        if archivo is None:
            raise ArchivoNoEncontradoError(archivo_id)

        return archivo
