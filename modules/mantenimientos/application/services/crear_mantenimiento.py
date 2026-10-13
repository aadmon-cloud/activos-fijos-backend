from datetime import UTC, datetime, timedelta

from modules.mantenimientos.application.dto.crear_mantenimiento_dto import CrearMantenimientoDTO
from modules.mantenimientos.application.dto.mantenimiento_dto import (
    MantenimientoDTO,
    mantenimiento_a_dto,
)
from modules.mantenimientos.application.ports.activo_resumen_port import ActivoResumenPort
from modules.mantenimientos.application.ports.mantenimiento_repository import (
    MantenimientoRepositoryPort,
)
from modules.mantenimientos.application.ports.solicitud_verificador_port import (
    SolicitudVerificadorPort,
)
from modules.mantenimientos.application.ports.verificador_tecnico_port import (
    VerificadorTecnicoPort,
)
from modules.mantenimientos.domain.entities import EstadoMantenimiento, Mantenimiento
from modules.mantenimientos.domain.errors import (
    ActivoNoEncontradoParaMantenimientoError,
    SolicitudNoValidaParaMantenimientoError,
    TecnicoInvalidoError,
)
from shared.application.notifications.enlaces import enlace
from shared.application.notifications.ports import NotificadorPort
from shared.domain.entities.audit import AuditPersona


class CrearMantenimientoService:
    def __init__(
        self,
        mantenimiento_repository: MantenimientoRepositoryPort,
        activo_resumen_port: ActivoResumenPort,
        verificador_tecnico: VerificadorTecnicoPort,
        solicitud_verificador: SolicitudVerificadorPort,
        notificador: NotificadorPort,
    ):
        self._mantenimiento_repository = mantenimiento_repository
        self._activo_resumen_port = activo_resumen_port
        self._verificador_tecnico = verificador_tecnico
        self._solicitud_verificador = solicitud_verificador
        self._notificador = notificador

    async def ejecutar(self, dto: CrearMantenimientoDTO) -> MantenimientoDTO:
        activo = await self._activo_resumen_port.obtener_resumen(dto.activo_id)
        if activo is None:
            raise ActivoNoEncontradoParaMantenimientoError(dto.activo_id)

        if not await self._verificador_tecnico.tiene_rol_mantenimiento(
            dto.tecnico_responsable_id
        ):
            raise TecnicoInvalidoError(dto.tecnico_responsable_id)

        # Una solicitud asociada se resuelve sola al completar el mantenimiento: tiene que ser real y
        # tratarse del mismo activo.
        if dto.solicitud_id is not None and not await self._solicitud_verificador.corresponde_al_activo(
            dto.solicitud_id, dto.activo_id
        ):
            raise SolicitudNoValidaParaMantenimientoError(dto.solicitud_id)

        proxima_fecha_sugerida = None
        if dto.frecuencia_dias is not None:
            proxima_fecha_sugerida = dto.fecha + timedelta(days=dto.frecuencia_dias)

        mantenimiento = Mantenimiento(
            id=None,
            activo_id=dto.activo_id,
            solicitud_id=dto.solicitud_id,
            tipo=dto.tipo,
            tecnico_responsable_id=dto.tecnico_responsable_id,
            fecha=dto.fecha,
            observaciones=dto.observaciones,
            costo=dto.costo,
            documentos=[],
            evidencias=[],
            estado=EstadoMantenimiento.PROGRAMADO,
            frecuencia_dias=dto.frecuencia_dias,
            proxima_fecha_sugerida=proxima_fecha_sugerida,
            alerta_enviada=False,
            creado_por=AuditPersona(
                id_persona=dto.creado_por_id,
                nombre=dto.creado_por_nombre,
                fecha=datetime.now(UTC),
            ),
            actualizado_por=None,
        )

        mantenimiento_guardado = await self._mantenimiento_repository.guardar(mantenimiento)

        nombre = f"{activo.nombre} ({activo.numero_inventario})" if activo.nombre else "un activo"
        await self._notificador.notificar(
            destinatarios=list(
                dict.fromkeys(
                    [f"usuario:{dto.tecnico_responsable_id}", f"usuario:{activo.responsable_id}"]
                )
            ),
            asunto=f"Mantenimiento programado: {nombre}",
            cuerpo=(
                f"Se programo un mantenimiento {dto.tipo.value} de {nombre} para el "
                f"{dto.fecha.strftime('%d/%m/%Y')}.\n\n"
                f"Ver el mantenimiento: {enlace(f'/mantenimientos/detalle?id={mantenimiento_guardado.id}')}"
            ),
        )

        return mantenimiento_a_dto(mantenimiento_guardado)
