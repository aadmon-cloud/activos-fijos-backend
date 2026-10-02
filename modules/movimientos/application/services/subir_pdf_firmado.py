from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.ports.storage_repository import StorageRepositoryPort
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.movimientos.domain.errors import ArchivoNoEsPdfError, MovimientoNoEncontradoError
from shared.domain.entities.audit_persona import AuditPersona

SUBCARPETA_PDFS_SALIDAS = "pdfs/salidas"


class SubirPdfFirmadoService:
    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        storage_repository: StorageRepositoryPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._storage_repository = storage_repository

    async def ejecutar(
        self,
        movimiento_id: str,
        nombre_archivo: str,
        contenido: bytes,
        actualizado_por: AuditPersona,
    ) -> Movimiento:
        """Raises:
        MovimientoNoEncontradoError: no existe una salida con ese id.
        ArchivoNoEsPdfError: el archivo subido no tiene extensión .pdf.
        """
        movimiento = await self._movimiento_repository.obtener_por_id(movimiento_id)
        if movimiento is None or movimiento.tipo != "salida":
            raise MovimientoNoEncontradoError(movimiento_id)
        if not nombre_archivo.lower().endswith(".pdf"):
            raise ArchivoNoEsPdfError(nombre_archivo)

        nombre_guardado = f"{movimiento_id}_{nombre_archivo}"
        ruta = await self._storage_repository.guardar(
            SUBCARPETA_PDFS_SALIDAS, nombre_guardado, contenido
        )

        movimiento_actualizado = movimiento.adjuntar_pdf_firmado(
            ruta, nombre_archivo, actualizado_por
        )
        return await self._movimiento_repository.actualizar(movimiento_actualizado)
