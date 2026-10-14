import logging
from dataclasses import replace
from datetime import UTC, datetime

from modules.movimientos.application.avisos import EventoMovimiento, avisar
from modules.movimientos.application.dto.acciones_movimiento_dto import ConfirmarDevolucionDTO
from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO, movimiento_a_dto
from modules.movimientos.application.emisor_actas import EmisorActas
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.seleccion_activos import (
    aplicar_a_activos,
    ahora_audit,
    reemplazar_items,
)
from modules.movimientos.domain.entities import (
    EstadoItemMovimiento,
    EstadoMovimiento,
    ItemMovimiento,
    LineaActa,
    Movimiento,
    ResultadoChequeo,
    SelloActa,
    TipoActa,
)
from modules.movimientos.domain.errors import (
    MovimientoNoEncontradoError,
    NingunActivoChequeadoError,
    OperacionSobreActivoFallidaError,
    TransicionEstadoMovimientoInvalidaError,
)
from modules.movimientos.domain.transiciones import ESTADOS_ITEM_DEVOLVIBLES, calcular_estado
from shared.application.notifications.ports import NotificadorPort

logger = logging.getLogger(__name__)

_ESTADO_DISPONIBLE = "disponible"
_ESTADO_PRESTADO = "prestado"
_OBSERVACION_NO_DEVUELTO = "Sigue fuera: no se recibio en este ingreso."


class ConfirmarDevolucionMovimientoService:
    """Cierra el chequeo de ingreso: se reciben de vuelta los activos chequeados como encontrados (o con novedad).

    El activo vuelve a `disponible` y a su responsable original; una novedad queda en el historial del activo. Los
    que no se encontraron (o no se chequearon) siguen fuera y se pueden recibir en otro ingreso. Se genera el acta
    de ingreso con el sello de administracion; el del responsable queda pendiente hasta que la acepte."""

    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        activo_movimiento: ActivoMovimientoPort,
        emisor_actas: EmisorActas,
        notificador: NotificadorPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._activo_movimiento = activo_movimiento
        self._emisor_actas = emisor_actas
        self._notificador = notificador

    async def ejecutar(self, dto: ConfirmarDevolucionDTO) -> MovimientoDTO:
        movimiento = await self._movimiento_repository.obtener_por_id(dto.id_movimiento)
        if movimiento is None:
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        devolvibles = [i for i in movimiento.items if i.estado in ESTADOS_ITEM_DEVOLVIBLES]
        if not devolvibles:
            raise TransicionEstadoMovimientoInvalidaError(movimiento.estado.value, "devuelto")

        recibidos = [i for i in devolvibles if _se_recibe(i)]
        if not recibidos:
            raise NingunActivoChequeadoError()

        siguen_fuera = [i for i in devolvibles if not _se_recibe(i)]
        audit = ahora_audit(dto.actor_id, dto.actor_nombre)
        ahora = datetime.now(UTC)

        await aplicar_a_activos(
            recibidos,
            aplicar=lambda item: self._devolver(item, movimiento, dto),
            deshacer=lambda item: self._deshacer_devolucion(item, movimiento, dto),
            error=OperacionSobreActivoFallidaError,
        )

        cambios: dict[str, ItemMovimiento] = {}
        for item in recibidos:
            chequeo = item.chequeo_ingreso
            cambios[item.activo_id] = replace(
                item,
                estado=EstadoItemMovimiento.DEVUELTO,
                recibido_por=audit,
                fecha_devolucion_real=ahora,
                novedad_devolucion=chequeo.observacion if chequeo.resultado == ResultadoChequeo.CON_NOVEDAD else None,
            )
        for item in siguen_fuera:
            # Se limpia la marca: en el siguiente ingreso se vuelve a chequear desde cero.
            cambios[item.activo_id] = replace(item, chequeo_ingreso=None)

        items = reemplazar_items(movimiento, cambios)
        estado = calcular_estado(movimiento.tipo, items, movimiento.estado)
        devuelto = replace(
            movimiento,
            items=items,
            estado=estado,
            fecha_devolucion_real=ahora if estado == EstadoMovimiento.DEVUELTO else None,
            actualizado_por=audit,
        )

        lineas = [
            LineaActa(
                activo_id=item.activo_id,
                resultado=item.chequeo_ingreso.resultado,
                observacion=item.chequeo_ingreso.observacion,
            )
            for item in recibidos
        ] + [
            LineaActa(
                activo_id=item.activo_id,
                resultado=ResultadoChequeo.NO_ENCONTRADO,
                observacion=(item.chequeo_ingreso.observacion if item.chequeo_ingreso else None)
                or _OBSERVACION_NO_DEVUELTO,
            )
            for item in siguen_fuera
        ]
        acta = await self._emisor_actas.emitir(
            devuelto,
            TipoActa.INGRESO,
            lineas,
            SelloActa(id_persona=dto.actor_id, nombre=dto.actor_nombre, correo=dto.actor_correo, fecha=audit.fecha),
        )

        guardado = await self._movimiento_repository.guardar(replace(devuelto, actas=[*devuelto.actas, acta]))
        await self._dejar_novedades_en_el_historial(guardado, [cambios[i.activo_id] for i in recibidos], dto)

        resumenes = await self._activo_movimiento.obtener_resumenes(movimiento.activo_ids)
        await avisar(self._notificador, EventoMovimiento.DEVOLUCION_CONFIRMADA, guardado, resumenes)

        return movimiento_a_dto(guardado)

    async def _devolver(
        self, item: ItemMovimiento, movimiento: Movimiento, dto: ConfirmarDevolucionDTO
    ) -> bool:
        # Dos cambios sobre el activo sin transaccion: si el segundo falla se deshace el primero.
        if not await self._activo_movimiento.cambiar_estado(
            item.activo_id, _ESTADO_DISPONIBLE, dto.actor_id, dto.actor_nombre
        ):
            return False

        if not await self._activo_movimiento.cambiar_responsable(
            item.activo_id, item.responsable_original_id, dto.actor_id, dto.actor_nombre
        ):
            await self._activo_movimiento.cambiar_estado(
                item.activo_id, _ESTADO_PRESTADO, dto.actor_id, dto.actor_nombre
            )
            return False

        return True

    async def _deshacer_devolucion(
        self, item: ItemMovimiento, movimiento: Movimiento, dto: ConfirmarDevolucionDTO
    ) -> None:
        await self._activo_movimiento.cambiar_responsable(
            item.activo_id, movimiento.usuario_destino_id, dto.actor_id, dto.actor_nombre
        )
        await self._activo_movimiento.cambiar_estado(
            item.activo_id, _ESTADO_PRESTADO, dto.actor_id, dto.actor_nombre
        )

    async def _dejar_novedades_en_el_historial(
        self, movimiento: Movimiento, items, dto: ConfirmarDevolucionDTO
    ) -> None:
        # La novedad tambien queda guardada en el movimiento: si dejar la nota falla, la devolucion ya hecha
        # no se revierte; se registra el fallo para repararlo.
        for item in items:
            if not item.novedad_devolucion:
                continue
            try:
                await self._activo_movimiento.registrar_nota(
                    item.activo_id,
                    f"Novedad al recibirlo de vuelta ({_descripcion(movimiento)}): {item.novedad_devolucion}",
                    movimiento.id,
                    dto.actor_id,
                    dto.actor_nombre,
                )
            except Exception:
                logger.exception(
                    "No se pudo registrar la novedad de devolucion en el historial del activo %s", item.activo_id
                )


def _se_recibe(item: ItemMovimiento) -> bool:
    return item.chequeo_ingreso is not None and item.chequeo_ingreso.resultado != ResultadoChequeo.NO_ENCONTRADO


def _descripcion(movimiento: Movimiento) -> str:
    if movimiento.evento_nombre:
        return f"salida al evento '{movimiento.evento_nombre}'"

    return "prestamo"
