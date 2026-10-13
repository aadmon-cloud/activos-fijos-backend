from functools import lru_cache

from modules.auditorias.application.ports.activos_asignados_port import ActivosAsignadosPort
from modules.auditorias.application.ports.auditoria_repository import AuditoriaRepositoryPort
from modules.auditorias.application.ports.generador_reporte_port import GeneradorReportePort
from modules.auditorias.application.ports.historial_activo_nota_port import (
    HistorialActivoNotaPort,
)
from modules.auditorias.application.ports.usuario_auditado_port import UsuarioAuditadoPort
from modules.auditorias.application.services.cerrar_auditoria import CerrarAuditoriaService
from modules.auditorias.application.services.iniciar_auditoria import IniciarAuditoriaService
from modules.auditorias.application.services.listar_auditorias import ListarAuditoriasService
from modules.auditorias.application.services.obtener_auditoria import ObtenerAuditoriaService
from modules.auditorias.application.services.obtener_pdf_auditoria import (
    ObtenerPdfAuditoriaService,
)
from modules.auditorias.application.services.reenviar_notificacion_auditoria import (
    ReenviarNotificacionAuditoriaService,
)
from modules.auditorias.application.services.verificar_item_auditoria import (
    VerificarItemAuditoriaService,
)
from modules.auditorias.infrastructure.persistence.mongo.activos_asignados_adapter import (
    MongoActivosAsignadosAdapter,
)
from modules.auditorias.infrastructure.persistence.mongo.auditoria_repository import (
    MongoAuditoriaRepository,
)
from modules.auditorias.infrastructure.persistence.mongo.historial_activo_nota_adapter import (
    MongoHistorialActivoNotaAdapter,
)
from modules.auditorias.infrastructure.persistence.mongo.usuario_auditado_adapter import (
    MongoUsuarioAuditadoAdapter,
)
from modules.auditorias.infrastructure.reportes.generador_reporte_pdf import GeneradorReportePdf
from shared.application.file_storage.ports import AlmacenArchivosPort
from shared.application.notifications.ports import NotificadorConAdjuntoPort
from shared.infrastructure.notifications.smtp_notificador import SMTPNotificador
from shared.infrastructure.persistence.mongo.almacen_archivos_gridfs import (
    MongoAlmacenArchivosGridFS,
)

_BUCKET_ARCHIVOS = "auditorias_archivos"


@lru_cache(maxsize=1)
def get_auditoria_repository() -> AuditoriaRepositoryPort:
    return MongoAuditoriaRepository()


@lru_cache(maxsize=1)
def get_activos_asignados() -> ActivosAsignadosPort:
    return MongoActivosAsignadosAdapter()


@lru_cache(maxsize=1)
def get_usuario_auditado() -> UsuarioAuditadoPort:
    return MongoUsuarioAuditadoAdapter()


@lru_cache(maxsize=1)
def get_historial_activo_nota() -> HistorialActivoNotaPort:
    return MongoHistorialActivoNotaAdapter()


@lru_cache(maxsize=1)
def get_generador_reporte() -> GeneradorReportePort:
    return GeneradorReportePdf()


@lru_cache(maxsize=1)
def get_almacen_archivos() -> AlmacenArchivosPort:
    return MongoAlmacenArchivosGridFS(bucket_name=_BUCKET_ARCHIVOS)


@lru_cache(maxsize=1)
def get_notificador() -> NotificadorConAdjuntoPort:
    return SMTPNotificador()


def get_iniciar_auditoria_service() -> IniciarAuditoriaService:
    return IniciarAuditoriaService(
        auditoria_repository=get_auditoria_repository(),
        usuario_auditado=get_usuario_auditado(),
        activos_asignados=get_activos_asignados(),
    )


def get_verificar_item_auditoria_service() -> VerificarItemAuditoriaService:
    return VerificarItemAuditoriaService(auditoria_repository=get_auditoria_repository())


def get_cerrar_auditoria_service() -> CerrarAuditoriaService:
    return CerrarAuditoriaService(
        auditoria_repository=get_auditoria_repository(),
        usuario_auditado=get_usuario_auditado(),
        historial_nota=get_historial_activo_nota(),
        generador_reporte=get_generador_reporte(),
        almacen_archivos=get_almacen_archivos(),
        notificador=get_notificador(),
    )


def get_reenviar_notificacion_auditoria_service() -> ReenviarNotificacionAuditoriaService:
    return ReenviarNotificacionAuditoriaService(
        auditoria_repository=get_auditoria_repository(),
        usuario_auditado=get_usuario_auditado(),
        almacen_archivos=get_almacen_archivos(),
        notificador=get_notificador(),
    )


def get_obtener_auditoria_service() -> ObtenerAuditoriaService:
    return ObtenerAuditoriaService(
        auditoria_repository=get_auditoria_repository(),
        usuario_auditado=get_usuario_auditado(),
    )


def get_listar_auditorias_service() -> ListarAuditoriasService:
    return ListarAuditoriasService(
        auditoria_repository=get_auditoria_repository(),
        usuario_auditado=get_usuario_auditado(),
    )


def get_obtener_pdf_auditoria_service() -> ObtenerPdfAuditoriaService:
    return ObtenerPdfAuditoriaService(
        auditoria_repository=get_auditoria_repository(),
        almacen_archivos=get_almacen_archivos(),
    )
