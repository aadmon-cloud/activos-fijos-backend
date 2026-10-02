from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.errors import ProductoNoEncontradoError
from modules.ubicaciones.application.dto.crear_ubicacion import CrearUbicacionInput
from modules.ubicaciones.application.ports.registrador_de_movimientos import (
    RegistradorDeMovimientosPort,
)
from modules.ubicaciones.application.ports.ubicacion_repository import UbicacionRepositoryPort
from modules.ubicaciones.domain.entities.ubicacion import Ubicacion
from modules.ubicaciones.domain.errors import UbicacionDuplicadaError
from shared.application.persistence.unit_of_work import UnitOfWorkFactory
from shared.domain.entities.audit_persona import AuditPersona


class CrearUbicacionService:
    def __init__(
        self,
        ubicacion_repository: UbicacionRepositoryPort,
        producto_repository: ProductoRepositoryPort,
        registrador_de_movimientos: RegistradorDeMovimientosPort,
        unit_of_work_factory: UnitOfWorkFactory,
    ):
        self._ubicacion_repository = ubicacion_repository
        self._producto_repository = producto_repository
        self._registrador_de_movimientos = registrador_de_movimientos
        self._unit_of_work_factory = unit_of_work_factory

    async def ejecutar(self, entrada: CrearUbicacionInput, creado_por: AuditPersona) -> Ubicacion:
        """Crea una ubicación y recalcula `productos.stock_actual` como la suma de
        todas las ubicaciones del producto, en una única transacción. Deja
        además una bitácora en `movimientos` (vía `RegistradorDeMovimientosPort`
        — inversión de dependencias, ver MIGRATION_PLAN.md).

        Raises:
            ProductoNoEncontradoError: no existe un producto con ese código.
            UbicacionDuplicadaError: el producto ya tiene una ubicación con ese nombre.
        """
        producto = await self._producto_repository.obtener_por_codigo(entrada.producto_codigo)
        if producto is None:
            raise ProductoNoEncontradoError(entrada.producto_codigo)

        if await self._ubicacion_repository.existe(entrada.producto_codigo, entrada.ubicacion):
            raise UbicacionDuplicadaError(entrada.producto_codigo, entrada.ubicacion)

        nueva_ubicacion = Ubicacion.crear(
            producto_codigo=entrada.producto_codigo,
            ubicacion=entrada.ubicacion,
            stock_fisico=entrada.cantidad,
            creado_por=creado_por,
        )

        async with self._unit_of_work_factory() as uow:
            ubicacion_creada = await self._ubicacion_repository.crear(nueva_ubicacion, uow=uow)
            todas = await self._ubicacion_repository.listar_por_producto(
                entrada.producto_codigo, uow=uow
            )
            nuevo_total = sum(u.stock_fisico for u in todas)
            await self._producto_repository.actualizar(
                producto.recalcular_stock(nuevo_total), uow=uow
            )
            await self._registrador_de_movimientos.registrar_creacion_ubicacion(
                producto_codigo=entrada.producto_codigo,
                ubicacion=entrada.ubicacion,
                cantidad=entrada.cantidad,
                creado_por=creado_por,
                uow=uow,
            )

        return ubicacion_creada
