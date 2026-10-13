from modules.solicitudes.application.dto.listar_solicitudes_dto import ListarSolicitudesDTO
from modules.solicitudes.application.dto.solicitud_dto import ListadoSolicitudesDTO
from modules.solicitudes.application.ports.resolutor_referencias import ResolutorReferenciasPort
from modules.solicitudes.application.ports.solicitud_repository import (
    SolicitudRepositoryPort,
    VisibilidadSolicitud,
)
from modules.solicitudes.application.services.enriquecimiento import con_nombres
from modules.solicitudes.domain.permisos import es_administrador

_LIMITE_MAXIMO = 1000


class ListarSolicitudesService:
    def __init__(
        self,
        solicitud_repository: SolicitudRepositoryPort,
        resolutor_referencias: ResolutorReferenciasPort,
    ):
        self._solicitud_repository = solicitud_repository
        self._resolutor_referencias = resolutor_referencias

    async def ejecutar(self, dto: ListarSolicitudesDTO) -> ListadoSolicitudesDTO:
        limit = min(dto.limit, _LIMITE_MAXIMO)

        # El administrador ve todo; los demas, solo lo que crearon o se asigno a su rol o area.
        visible_para = (
            None
            if es_administrador(dto.actor_rol)
            else VisibilidadSolicitud(
                actor_id=dto.actor_id, rol=dto.actor_rol, area_id=dto.actor_area_id
            )
        )
        filtros = dict(
            tipo=dto.tipo,
            estado=dto.estado,
            activo_id=dto.activo_id,
            rol_asignado=dto.rol_asignado,
            area_id=dto.area_id,
            creado_por_id=dto.creado_por_id,
            visible_para=visible_para,
        )

        solicitudes = await self._solicitud_repository.listar(**filtros, skip=dto.skip, limit=limit)
        total = await self._solicitud_repository.contar(**filtros)

        return ListadoSolicitudesDTO(
            items=await con_nombres(solicitudes, self._resolutor_referencias),
            total=total,
            skip=dto.skip,
            limit=limit,
        )
