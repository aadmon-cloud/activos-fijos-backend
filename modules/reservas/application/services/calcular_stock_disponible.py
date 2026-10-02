from modules.reservas.application.dto.stock_disponible_resultado import (
    StockDisponibleResultado,
)
from modules.reservas.application.ports.reserva_repository import ReservaRepositoryPort
from modules.ubicaciones.application.ports.ubicacion_repository import UbicacionRepositoryPort
from modules.ubicaciones.domain.errors import UbicacionNoEncontradaError


class CalcularStockDisponibleService:
    def __init__(
        self,
        ubicacion_repository: UbicacionRepositoryPort,
        reserva_repository: ReservaRepositoryPort,
    ):
        self._ubicacion_repository = ubicacion_repository
        self._reserva_repository = reserva_repository

    async def ejecutar(
        self, producto_codigo: str, ubicacion: str, session_id_actual: str | None = None
    ) -> StockDisponibleResultado:
        """Raises:
        UbicacionNoEncontradaError: no existe esa ubicación para ese producto.
        """
        ubicacion_entidad = await self._ubicacion_repository.obtener(producto_codigo, ubicacion)
        if ubicacion_entidad is None:
            raise UbicacionNoEncontradaError(producto_codigo, ubicacion)

        reservas_activas = await self._reserva_repository.listar_activas_por_producto_ubicacion(
            producto_codigo, ubicacion
        )

        reservado_otros = 0
        reservado_actual = 0
        for reserva in reservas_activas:
            es_actual = session_id_actual is not None and reserva.session_id == session_id_actual
            for item in reserva.items:
                if item.producto_codigo != producto_codigo or item.ubicacion != ubicacion:
                    continue
                if es_actual:
                    reservado_actual += item.cantidad
                else:
                    reservado_otros += item.cantidad

        disponible = max(0, ubicacion_entidad.stock_fisico - reservado_otros - reservado_actual)

        return StockDisponibleResultado(
            producto_codigo=producto_codigo,
            ubicacion=ubicacion,
            stock_fisico=ubicacion_entidad.stock_fisico,
            reservado_otros=reservado_otros,
            reservado_actual=reservado_actual,
            disponible=disponible,
        )
