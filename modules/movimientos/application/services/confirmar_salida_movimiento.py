from dataclasses import replace
from datetime import UTC, datetime

from modules.movimientos.application.avisos import EventoMovimiento, avisar
from modules.movimientos.application.dto.acciones_movimiento_dto import ConfirmarSalidaDTO
from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO, movimiento_a_dto
from modules.movimientos.application.ports.activo_movimiento_port import (
    ActivoMovimientoPort,
    ActivoResumenMovimiento,
)
from modules.movimientos.application.ports.generador_comprobante_port import (
    GeneradorComprobantePort,
)
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.ports.resolutor_nombres_port import (
    ReferenciasMovimiento,
    ResolutorNombresMovimientoPort,
)
from modules.movimientos.application.seleccion_activos import (
    aplicar_a_activos,
    ahora_audit,
    elegir_activos,
    reemplazar_items,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EtapaRechazo,
    ItemMovimiento,
    Movimiento,
    TipoMovimiento,
)
from modules.movimientos.domain.errors import (
    MovimientoNoEncontradoError,
    OperacionSobreActivoFallidaError,
    TransicionEstadoMovimientoInvalidaError,
)
from modules.movimientos.domain.transiciones import calcular_estado
from shared.application.file_storage.ports import AlmacenArchivosPort
from shared.application.notifications.ports import NotificadorPort

_ESTADO_PRESTADO = "prestado"
_ESTADO_DISPONIBLE = "disponible"
_NOMBRE_COMPROBANTE = "comprobante.pdf"
_MOTIVO_POR_DEFECTO = "No autorizado por administracion en la salida."


class ConfirmarSalidaMovimientoService:
    """Aprobacion final de administracion de un prestamo o salida a evento: elige que activos salen (todos o solo
    algunos). Los que salen pasan a `prestado` y a cargo del destinatario; los demas quedan rechazados."""

    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        activo_movimiento: ActivoMovimientoPort,
        resolutor_nombres: ResolutorNombresMovimientoPort,
        generador_comprobante: GeneradorComprobantePort,
        almacen_archivos: AlmacenArchivosPort,
        notificador: NotificadorPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._activo_movimiento = activo_movimiento
        self._resolutor_nombres = resolutor_nombres
        self._generador_comprobante = generador_comprobante
        self._almacen_archivos = almacen_archivos
        self._notificador = notificador

    async def ejecutar(self, dto: ConfirmarSalidaDTO) -> MovimientoDTO:
        movimiento = await self._movimiento_repository.obtener_por_id(dto.id_movimiento)
        if movimiento is None:
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        invalido = TransicionEstadoMovimientoInvalidaError(movimiento.estado.value, "en_curso")
        if movimiento.tipo == TipoMovimiento.BAJA:
            raise invalido

        pendientes = [i for i in movimiento.items if i.estado == EstadoItemMovimiento.PENDIENTE_ADMIN]
        salen = elegir_activos(movimiento, pendientes, dto.activo_ids, invalido)
        ids_salen = {item.activo_id for item in salen}
        no_salen = [item for item in pendientes if item.activo_id not in ids_salen]
        audit = ahora_audit(dto.actor_id, dto.actor_nombre)

        await aplicar_a_activos(
            salen,
            aplicar=lambda item: self._sacar(item, movimiento.usuario_destino_id, dto),
            deshacer=lambda item: self._deshacer_salida(item, dto),
            error=OperacionSobreActivoFallidaError,
        )

        cambios: dict[str, ItemMovimiento] = {
            item.activo_id: replace(item, estado=EstadoItemMovimiento.EN_CURSO) for item in salen
        }
        for item in no_salen:
            cambios[item.activo_id] = replace(
                item,
                estado=EstadoItemMovimiento.RECHAZADO,
                rechazado_por=audit,
                etapa_rechazo=EtapaRechazo.ADMINISTRACION,
                motivo_rechazo=(dto.motivo_no_incluidos or "").strip() or _MOTIVO_POR_DEFECTO,
            )

        items = reemplazar_items(movimiento, cambios)
        confirmado = replace(
            movimiento,
            items=items,
            estado=calcular_estado(movimiento.tipo, items, movimiento.estado),
            aprobado_por_admin=audit,
            fecha_entrega_real=datetime.now(UTC),
            actualizado_por=audit,
        )

        resumenes = await self._activo_movimiento.obtener_resumenes(movimiento.activo_ids)
        if movimiento.tipo == TipoMovimiento.SALIDA_EVENTO:
            confirmado = replace(
                confirmado,
                comprobante_archivo_id=await self._generar_comprobante(confirmado, salen, resumenes),
            )

        guardado = await self._movimiento_repository.guardar(confirmado)
        await avisar(self._notificador, EventoMovimiento.SALIDA_CONFIRMADA, guardado, resumenes)

        return movimiento_a_dto(guardado)

    async def _sacar(self, item: ItemMovimiento, destino_id: str | None, dto: ConfirmarSalidaDTO) -> bool:
        # Dos cambios sobre el activo sin transaccion: si el segundo falla se deshace el primero, para no
        # dejarlo "prestado" con el responsable de antes.
        if not await self._activo_movimiento.cambiar_estado(
            item.activo_id, _ESTADO_PRESTADO, dto.actor_id, dto.actor_nombre
        ):
            return False

        if not await self._activo_movimiento.cambiar_responsable(
            item.activo_id, destino_id, dto.actor_id, dto.actor_nombre
        ):
            await self._activo_movimiento.cambiar_estado(
                item.activo_id, _ESTADO_DISPONIBLE, dto.actor_id, dto.actor_nombre
            )
            return False

        return True

    async def _deshacer_salida(self, item: ItemMovimiento, dto: ConfirmarSalidaDTO) -> None:
        await self._activo_movimiento.cambiar_responsable(
            item.activo_id, item.responsable_original_id, dto.actor_id, dto.actor_nombre
        )
        await self._activo_movimiento.cambiar_estado(
            item.activo_id, _ESTADO_DISPONIBLE, dto.actor_id, dto.actor_nombre
        )

    async def _generar_comprobante(
        self,
        movimiento: Movimiento,
        salen: list[ItemMovimiento],
        resumenes: dict[str, ActivoResumenMovimiento],
    ) -> str:
        nombres = await self._resolutor_nombres.resolver(
            ReferenciasMovimiento(usuario_ids={movimiento.usuario_destino_id})
        )
        lineas = [_linea_activo(resumenes.get(item.activo_id), item.activo_id) for item in salen]
        contenido_pdf = await self._generador_comprobante.generar_pdf(
            movimiento,
            lineas,
            nombres.usuarios.get(movimiento.usuario_destino_id, movimiento.usuario_destino_id),
        )

        return await self._almacen_archivos.guardar(
            movimiento.id, _NOMBRE_COMPROBANTE, contenido_pdf, "application/pdf"
        )


def _linea_activo(resumen: ActivoResumenMovimiento | None, activo_id: str) -> str:
    if resumen is None or not resumen.nombre:
        return activo_id

    return f"{resumen.numero_inventario} - {resumen.nombre}" if resumen.numero_inventario else resumen.nombre
