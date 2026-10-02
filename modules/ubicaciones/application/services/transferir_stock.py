from modules.ubicaciones.application.dto.transferir_stock import TransferirStockInput
from modules.ubicaciones.application.ports.registrador_de_movimientos import (
    RegistradorDeMovimientosPort,
)
from modules.ubicaciones.application.ports.ubicacion_repository import UbicacionRepositoryPort
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from modules.ubicaciones.domain.errors import StockInsuficienteError, UbicacionNoEncontradaError
from shared.application.persistence.unit_of_work import UnitOfWorkFactory
from shared.domain.entities.audit_persona import AuditPersona


class TransferirStockService:
    def __init__(
        self,
        ubicacion_repository: UbicacionRepositoryPort,
        registrador_de_movimientos: RegistradorDeMovimientosPort,
        unit_of_work_factory: UnitOfWorkFactory,
    ):
        self._ubicacion_repository = ubicacion_repository
        self._registrador_de_movimientos = registrador_de_movimientos
        self._unit_of_work_factory = unit_of_work_factory

    async def ejecutar(
        self,
        producto_codigo: str,
        entrada: TransferirStockInput,
        actualizado_por: AuditPersona,
    ) -> None:
        """Mueve stock entre dos ubicaciones del mismo producto. El total del
        producto no cambia (se redistribuye), por eso no toca `productos.stock_actual`.
        Deja además una bitácora en `movimientos` (vía `RegistradorDeMovimientosPort`
        — inversión de dependencias, ver MIGRATION_PLAN.md).

        Raises:
            UbicacionNoEncontradaError: no existe la ubicación de origen.
            StockInsuficienteError: el origen no tiene suficiente stock físico.
        """
        origen = await self._ubicacion_repository.obtener(producto_codigo, entrada.origen)
        if origen is None:
            raise UbicacionNoEncontradaError(producto_codigo, entrada.origen)

        if origen.stock_fisico < entrada.cantidad:
            raise StockInsuficienteError(entrada.origen, origen.stock_fisico, entrada.cantidad)

        destino = await self._ubicacion_repository.obtener(producto_codigo, entrada.destino)
        origen_actualizado = origen.actualizar_stock_fisico(
            origen.stock_fisico - entrada.cantidad, actualizado_por
        )

        async with self._unit_of_work_factory() as uow:
            await self._ubicacion_repository.actualizar(origen_actualizado, uow=uow)
            if destino is not None:
                destino_actualizado = destino.actualizar_stock_fisico(
                    destino.stock_fisico + entrada.cantidad, actualizado_por
                )
                await self._ubicacion_repository.actualizar(destino_actualizado, uow=uow)
            else:
                nueva_destino = Ubicacion.crear(
                    producto_codigo=producto_codigo,
                    ubicacion=entrada.destino,
                    stock_fisico=entrada.cantidad,
                    creado_por=actualizado_por,
                )
                await self._ubicacion_repository.crear(nueva_destino, uow=uow)

            await self._registrador_de_movimientos.registrar_transferencia_stock(
                producto_codigo=producto_codigo,
                ubicacion_origen=entrada.origen,
                ubicacion_destino=entrada.destino,
                cantidad=entrada.cantidad,
                creado_por=actualizado_por,
                uow=uow,
            )
