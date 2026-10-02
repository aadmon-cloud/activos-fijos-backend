from modules.reservas.application.dto.ajustar_reserva import AjustarReservaInput
from modules.reservas.application.ports.reserva_repository import ReservaRepositoryPort
from modules.reservas.application.services.calcular_stock_disponible import (
    CalcularStockDisponibleService,
)
from modules.reservas.domain.entities.reserva import ItemReserva, Reserva
from modules.reservas.domain.errors import StockDisponibleInsuficienteError
from shared.domain.entities.audit_persona import AuditPersona


class AjustarReservaService:
    def __init__(
        self,
        reserva_repository: ReservaRepositoryPort,
        calcular_stock_disponible_service: CalcularStockDisponibleService,
    ):
        self._reserva_repository = reserva_repository
        self._calcular_stock_disponible_service = calcular_stock_disponible_service

    async def ejecutar(
        self,
        session_id: str,
        entrada: AjustarReservaInput,
        usuario_actual: AuditPersona,
    ) -> Reserva | None:
        """Crea la reserva si no existía (solo con los ajustes de diferencia
        positiva) o aplica los ajustes sobre la existente. Si no quedan items
        tras aplicar los ajustes, se elimina el documento completo.

        Raises:
            StockDisponibleInsuficienteError: un ajuste positivo excede el stock disponible.
        """
        reserva = await self._reserva_repository.obtener_por_session_id(session_id)

        if reserva is None:
            return await self._crear_desde_ajustes(session_id, entrada, usuario_actual)

        for ajuste in entrada.ajustes:
            if ajuste.diferencia > 0:
                await self._validar_stock_disponible(ajuste, session_id)
            reserva = reserva.aplicar_ajuste(
                ajuste.producto_codigo, ajuste.ubicacion, ajuste.diferencia, usuario_actual
            )

        if entrada.datos_adicionales is not None:
            reserva = reserva.model_copy(update={"datos_adicionales": entrada.datos_adicionales})

        if reserva.sin_items:
            await self._reserva_repository.eliminar(session_id)
            return None

        return await self._reserva_repository.actualizar(reserva)

    async def _crear_desde_ajustes(
        self, session_id: str, entrada: AjustarReservaInput, creado_por: AuditPersona
    ) -> Reserva | None:
        items_iniciales = []
        for ajuste in entrada.ajustes:
            if ajuste.diferencia <= 0:
                continue
            await self._validar_stock_disponible(ajuste, session_id)
            items_iniciales.append(
                ItemReserva(
                    producto_codigo=ajuste.producto_codigo,
                    ubicacion=ajuste.ubicacion,
                    cantidad=ajuste.diferencia,
                )
            )

        if not items_iniciales:
            return None

        nueva_reserva = Reserva.crear(
            session_id, items_iniciales, entrada.datos_adicionales, creado_por
        )
        return await self._reserva_repository.crear(nueva_reserva)

    async def _validar_stock_disponible(self, ajuste, session_id: str) -> None:
        resultado = await self._calcular_stock_disponible_service.ejecutar(
            ajuste.producto_codigo, ajuste.ubicacion, session_id
        )
        if resultado.disponible < ajuste.diferencia:
            raise StockDisponibleInsuficienteError(
                ajuste.producto_codigo,
                ajuste.ubicacion,
                resultado.disponible,
                ajuste.diferencia,
            )
