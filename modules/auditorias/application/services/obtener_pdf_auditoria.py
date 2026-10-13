from modules.auditorias.application.ports.auditoria_repository import AuditoriaRepositoryPort
from modules.auditorias.domain.errors import (
    AuditoriaNoEncontradaError,
    PdfAuditoriaNoDisponibleError,
)
from shared.application.file_storage.ports import AlmacenArchivosPort, ArchivoAlmacenado


class ObtenerPdfAuditoriaService:
    def __init__(
        self,
        auditoria_repository: AuditoriaRepositoryPort,
        almacen_archivos: AlmacenArchivosPort,
    ):
        self._auditoria_repository = auditoria_repository
        self._almacen_archivos = almacen_archivos

    async def ejecutar(self, id_auditoria: str) -> ArchivoAlmacenado:
        auditoria = await self._auditoria_repository.obtener_por_id(id_auditoria)
        if auditoria is None:
            raise AuditoriaNoEncontradaError(id_auditoria)
        if auditoria.pdf_archivo_id is None:
            raise PdfAuditoriaNoDisponibleError(id_auditoria)

        archivo = await self._almacen_archivos.obtener(auditoria.pdf_archivo_id)
        if archivo is None:
            raise PdfAuditoriaNoDisponibleError(id_auditoria)
        return archivo
