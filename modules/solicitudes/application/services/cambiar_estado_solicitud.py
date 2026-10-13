from dataclasses import replace
from datetime import UTC, datetime

from modules.solicitudes.application.dto.cambiar_estado_solicitud_dto import (
    CambiarEstadoSolicitudDTO,
)
from modules.solicitudes.application.dto.solicitud_dto import SolicitudDTO, solicitud_a_dto
from modules.solicitudes.application.ports.activo_estado_port import ActivoEstadoPort
from modules.solicitudes.application.ports.solicitud_repository import SolicitudRepositoryPort
from modules.solicitudes.domain.efecto_en_activo import ETIQUETAS_ESTADO_ACTIVO, efecto_en_activo
from modules.solicitudes.domain.entities import EntradaSeguimiento, Solicitud
from modules.solicitudes.domain.errors import (
    SolicitudNoEncontradaError,
    SolicitudSinPermisoError,
    TransicionEstadoSolicitudInvalidaError,
)
from modules.solicitudes.domain.permisos import puede_cambiar_a, puede_ver
from modules.solicitudes.domain.transiciones import es_transicion_valida
from shared.application.notifications.enlaces import enlace
from shared.application.notifications.ports import NotificadorPort
from shared.domain.entities.audit import AuditPersona


def _etiqueta(estado_activo: str) -> str:
    return ETIQUETAS_ESTADO_ACTIVO.get(estado_activo, estado_activo)


class CambiarEstadoSolicitudService:
    def __init__(
        self,
        solicitud_repository: SolicitudRepositoryPort,
        notificador: NotificadorPort,
        activo_estado: ActivoEstadoPort,
    ):
        self._solicitud_repository = solicitud_repository
        self._notificador = notificador
        self._activo_estado = activo_estado

    async def ejecutar(self, dto: CambiarEstadoSolicitudDTO) -> SolicitudDTO:
        solicitud = await self._solicitud_repository.obtener_por_id(dto.id_solicitud)
        if solicitud is None:
            raise SolicitudNoEncontradaError(dto.id_solicitud)

        # Sin acceso a la solicitud: se responde como si no existiera.
        if not puede_ver(solicitud, dto.actor_id, dto.actor_rol, dto.actor_area_id):
            raise SolicitudNoEncontradaError(dto.id_solicitud)

        if not puede_cambiar_a(
            solicitud, dto.estado_nuevo, dto.actor_id, dto.actor_rol, dto.actor_area_id
        ):
            raise SolicitudSinPermisoError(dto.id_solicitud)

        if not es_transicion_valida(solicitud.estado, dto.estado_nuevo):
            raise TransicionEstadoSolicitudInvalidaError(
                solicitud.estado.value, dto.estado_nuevo.value
            )

        audit = AuditPersona(
            id_persona=dto.actor_id, nombre=dto.actor_nombre, fecha=datetime.now(UTC)
        )

        nueva_entrada = EntradaSeguimiento(
            autor=audit,
            comentario=dto.comentario or f"Estado cambiado a '{dto.estado_nuevo.value}'.",
            estado_anterior=solicitud.estado.value,
            estado_nuevo=dto.estado_nuevo.value,
        )

        # El activo se actualiza antes de guardar la solicitud: si falla, la solicitud no cambia y
        # no quedan los dos desalineados. Lo que se hizo (o no) con el activo queda en el seguimiento.
        entradas = [nueva_entrada]
        nota_activo = await self._aplicar_efecto_en_activo(solicitud, dto, audit)
        if nota_activo is not None:
            entradas.append(nota_activo)

        solicitud_actualizada = replace(
            solicitud,
            estado=dto.estado_nuevo,
            seguimiento=[*solicitud.seguimiento, *entradas],
            actualizado_por=audit,
        )

        solicitud_guardada = await self._solicitud_repository.guardar(solicitud_actualizada)

        await self._notificador.notificar(
            destinatarios=[f"usuario:{solicitud.creado_por.id_persona}"],
            asunto=f"Solicitud actualizada a '{dto.estado_nuevo.value}'",
            cuerpo=(
                f"Tu solicitud de {solicitud.tipo.value.replace('_', ' ')} cambio a "
                f"'{dto.estado_nuevo.value}'.\n\n{nueva_entrada.comentario}\n\n"
                f"Ver la solicitud: {enlace(f'/solicitudes/detalle?id={solicitud.id}')}"
            ),
        )

        return solicitud_a_dto(solicitud_guardada)

    async def _aplicar_efecto_en_activo(
        self, solicitud: Solicitud, dto: CambiarEstadoSolicitudDTO, audit: AuditPersona
    ) -> EntradaSeguimiento | None:
        """Cambia el estado del activo segun el tipo y el estado de la solicitud, si la regla lo pide."""
        efecto = efecto_en_activo(solicitud.tipo, dto.estado_nuevo)
        if efecto is None:
            return None

        estado_actual = await self._activo_estado.obtener_estado(solicitud.activo_id)
        if estado_actual is None or estado_actual == efecto.estado_destino:
            return None

        if efecto.solo_si_actual is not None and estado_actual != efecto.solo_si_actual:
            return None

        cambiado = await self._activo_estado.cambiar_estado(
            solicitud.activo_id, efecto.estado_destino, dto.actor_id, dto.actor_nombre
        )

        origen, destino = _etiqueta(estado_actual), _etiqueta(efecto.estado_destino)
        comentario = (
            f"El estado del activo cambió de '{origen}' a '{destino}'."
            if cambiado
            else f"No se cambió el estado del activo: no puede pasar de '{origen}' a '{destino}'. "
            "Revíselo manualmente."
        )

        return EntradaSeguimiento(
            autor=audit, comentario=comentario, estado_anterior=None, estado_nuevo=None
        )
