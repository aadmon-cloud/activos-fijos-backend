from datetime import UTC, datetime

from modules.solicitudes.application.dto.crear_solicitud_dto import CrearSolicitudDTO
from modules.solicitudes.application.dto.solicitud_dto import SolicitudDTO, solicitud_a_dto
from modules.solicitudes.application.ports.activo_resumen_port import ActivoResumenPort
from modules.solicitudes.application.ports.solicitud_repository import SolicitudRepositoryPort
from modules.solicitudes.domain.entities import EstadoSolicitud, Solicitud, TipoSolicitud
from modules.solicitudes.domain.errors import (
    ActivoNoAsignadoError,
    ActivoNoEncontradoParaSolicitudError,
    DescripcionVaciaError,
)
from shared.application.notifications.ports import NotificadorPort
from shared.domain.entities.audit import AuditPersona

_ROL_ADMINISTRADOR_GENERAL = "administrador_general"

_TIPOS_POR_ROL = {
    TipoSolicitud.MANTENIMIENTO: "mantenimiento",
    TipoSolicitud.CAMBIO: "tecnologia",
}


class CrearSolicitudService:
    def __init__(
        self,
        solicitud_repository: SolicitudRepositoryPort,
        activo_resumen_port: ActivoResumenPort,
        notificador: NotificadorPort,
    ):
        self._solicitud_repository = solicitud_repository
        self._activo_resumen_port = activo_resumen_port
        self._notificador = notificador

    async def ejecutar(self, dto: CrearSolicitudDTO) -> SolicitudDTO:
        descripcion = dto.descripcion.strip()
        if not descripcion:
            raise DescripcionVaciaError()

        activo = await self._activo_resumen_port.obtener_resumen(dto.activo_id)
        if activo is None:
            raise ActivoNoEncontradoParaSolicitudError(dto.activo_id)

        es_responsable = dto.creado_por_id == activo.responsable_id
        es_administrador = dto.creado_por_rol == _ROL_ADMINISTRADOR_GENERAL
        if not es_responsable and not es_administrador:
            raise ActivoNoAsignadoError(dto.activo_id)

        rol_asignado = _TIPOS_POR_ROL.get(dto.tipo)
        area_id = activo.area_id if rol_asignado is None else None

        solicitud = Solicitud(
            id=None,
            tipo=dto.tipo,
            activo_id=dto.activo_id,
            descripcion=descripcion,
            prioridad=dto.prioridad,
            evidencias=dto.evidencias,
            estado=EstadoSolicitud.PENDIENTE,
            rol_asignado=rol_asignado,
            area_id=area_id,
            seguimiento=[],
            creado_por=AuditPersona(
                id_persona=dto.creado_por_id,
                nombre=dto.creado_por_nombre,
                fecha=datetime.now(UTC),
            ),
            actualizado_por=None,
        )

        solicitud_guardada = await self._solicitud_repository.guardar(solicitud)

        destinatario = f"rol:{rol_asignado}" if rol_asignado else f"area:{area_id}"
        await self._notificador.notificar(
            destinatarios=[destinatario],
            asunto=f"Nueva solicitud de {dto.tipo.value}",
            cuerpo=descripcion,
        )

        return solicitud_a_dto(solicitud_guardada)
