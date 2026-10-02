from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.domain.entities.movimiento import Movimiento
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.ubicaciones.application.ports.registrador_de_movimientos import (
    RegistradorDeMovimientosPort,
)
from shared.application.persistence.unit_of_work import UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona


class MovimientosRegistradorDeMovimientosAdapter(RegistradorDeMovimientosPort):
    """Implementa el puerto que posee `ubicaciones` — vive en `movimientos`
    porque es quien sabe cómo construir y persistir un `Movimiento`. Cableado
    únicamente en la capa de dependencias (composition root), nunca importado
    directamente por `modules.ubicaciones.application`."""

    def __init__(
        self,
        movimiento_repository: MovimientoRepositoryPort,
        producto_repository: ProductoRepositoryPort,
    ):
        self._movimiento_repository = movimiento_repository
        self._producto_repository = producto_repository

    async def registrar_creacion_ubicacion(
        self,
        producto_codigo: str,
        ubicacion: str,
        cantidad: int,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort | None = None,
    ) -> None:
        producto_nombre = await self._resolver_nombre(producto_codigo)
        movimiento = Movimiento.registrar_creacion_ubicacion(
            producto_codigo=producto_codigo,
            producto_nombre=producto_nombre,
            ubicacion=ubicacion,
            cantidad=cantidad,
            creado_por=creado_por,
        )
        await self._movimiento_repository.crear(movimiento, uow=uow)

    async def registrar_transferencia_stock(
        self,
        producto_codigo: str,
        ubicacion_origen: str,
        ubicacion_destino: str,
        cantidad: int,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort | None = None,
    ) -> None:
        producto_nombre = await self._resolver_nombre(producto_codigo)
        movimiento = Movimiento.registrar_transferencia_ubicacion(
            producto_codigo=producto_codigo,
            producto_nombre=producto_nombre,
            ubicacion_origen=ubicacion_origen,
            ubicacion_destino=ubicacion_destino,
            cantidad=cantidad,
            creado_por=creado_por,
        )
        await self._movimiento_repository.crear(movimiento, uow=uow)

    async def _resolver_nombre(self, producto_codigo: str) -> str:
        producto = await self._producto_repository.obtener_por_codigo(producto_codigo)
        return producto.nombre if producto is not None else producto_codigo
