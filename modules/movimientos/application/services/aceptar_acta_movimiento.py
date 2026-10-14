from dataclasses import replace
from datetime import UTC, datetime

from modules.movimientos.application.avisos import EventoMovimiento, avisar
from modules.movimientos.application.dto.chequeo_movimiento_dto import AceptarActaDTO
from modules.movimientos.application.dto.movimiento_dto import MovimientoDTO, movimiento_a_dto
from modules.movimientos.application.emisor_actas import EmisorActas
from modules.movimientos.application.ports.activo_movimiento_port import ActivoMovimientoPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.domain.entities import SelloActa
from modules.movimientos.domain.errors import (
    ActaNoEncontradaError,
    ActaYaAceptadaError,
    MovimientoNoEncontradoError,
    SoloElResponsableAceptaElActaError,
)
from modules.movimientos.domain.permisos import puede_aceptar_acta
from shared.application.notifications.ports import NotificadorPort


class AceptarActaMovimientoService:
    """Quien retira o devuelve los activos acepta el acta: queda su sello (nombre y correo) y el PDF se emite
    completo, con los dos sellos."""

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

    async def ejecutar(self, dto: AceptarActaDTO) -> MovimientoDTO:
        movimiento = await self._movimiento_repository.obtener_por_id(dto.id_movimiento)
        if movimiento is None:
            raise MovimientoNoEncontradoError(dto.id_movimiento)

        acta = movimiento.acta(dto.acta_id)
        if acta is None:
            raise ActaNoEncontradaError(dto.acta_id)

        if dto.actor_id != movimiento.usuario_destino_id:
            raise SoloElResponsableAceptaElActaError()
        if not puede_aceptar_acta(movimiento, acta, dto.actor_id):
            raise ActaYaAceptadaError(dto.acta_id)

        aceptada = await self._emisor_actas.aceptar(
            movimiento,
            acta,
            SelloActa(
                id_persona=dto.actor_id,
                nombre=dto.actor_nombre,
                correo=dto.actor_correo,
                fecha=datetime.now(UTC),
            ),
        )
        actas = [aceptada if existente.id == acta.id else existente for existente in movimiento.actas]

        # El comprobante historico apunta al acta de salida mas reciente: debe seguir apuntando al PDF vigente.
        comprobante = (
            aceptada.archivo_id
            if movimiento.comprobante_archivo_id == acta.archivo_id
            else movimiento.comprobante_archivo_id
        )
        guardado = await self._movimiento_repository.guardar(
            replace(movimiento, actas=actas, comprobante_archivo_id=comprobante)
        )

        resumenes = await self._activo_movimiento.obtener_resumenes(movimiento.activo_ids)
        await avisar(self._notificador, EventoMovimiento.ACTA_ACEPTADA, guardado, resumenes, acta=aceptada)

        return movimiento_a_dto(guardado)
