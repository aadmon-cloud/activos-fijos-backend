from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.errors import ProductoNoEncontradoError
from modules.ubicaciones.application.dto.actualizar_ubicacion import ActualizarUbicacionInput
from modules.ubicaciones.application.ports.ubicacion_repository import UbicacionRepositoryPort
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from modules.ubicaciones.domain.errors import UbicacionNoEncontradaError
from shared.application.persistence.unit_of_work import UnitOfWorkFactory
from shared.domain.entities.audit_persona import AuditPersona


class ActualizarUbicacionService:
    def __init__(
        self,
        ubicacion_repository: UbicacionRepositoryPort,
        producto_repository: ProductoRepositoryPort,
        unit_of_work_factory: UnitOfWorkFactory,
    ):
        self._ubicacion_repository = ubicacion_repository
        self._producto_repository = producto_repository
        self._unit_of_work_factory = unit_of_work_factory

    async def ejecutar(
        self,
        producto_codigo: str,
        ubicacion: str,
        entrada: ActualizarUbicacionInput,
        actualizado_por: AuditPersona,
    ) -> Ubicacion:
        """Raises:
        UbicacionNoEncontradaError: no existe esa ubicación para ese producto.
        ProductoNoEncontradoError: no existe el producto (inconsistencia de datos).
        """
        ubicacion_actual = await self._ubicacion_repository.obtener(producto_codigo, ubicacion)
        if ubicacion_actual is None:
            raise UbicacionNoEncontradaError(producto_codigo, ubicacion)

        producto = await self._producto_repository.obtener_por_codigo(producto_codigo)
        if producto is None:
            raise ProductoNoEncontradoError(producto_codigo)

        ubicacion_actualizada = ubicacion_actual.actualizar_stock_fisico(
            entrada.cantidad, actualizado_por
        )

        async with self._unit_of_work_factory() as uow:
            resultado = await self._ubicacion_repository.actualizar(
                ubicacion_actualizada, uow=uow
            )
            todas = await self._ubicacion_repository.listar_por_producto(
                producto_codigo, uow=uow
            )
            nuevo_total = sum(u.stock_fisico for u in todas)
            await self._producto_repository.actualizar(
                producto.recalcular_stock(nuevo_total), uow=uow
            )

        return resultado
