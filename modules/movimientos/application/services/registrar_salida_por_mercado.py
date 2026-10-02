from modules.mercados_predefinidos.application.ports.mercado_predefinido_repository import (
    MercadoPredefinidoRepositoryPort,
)
from modules.mercados_predefinidos.domain.errors import MercadoNoEncontradoError
from modules.movimientos.application.dto.registrar_salida_por_mercado import (
    RegistrarSalidaPorMercadoInput,
)
from modules.movimientos.application.ports.generador_secuencial import GeneradorSecuencialPort
from modules.movimientos.application.ports.movimiento_repository import MovimientoRepositoryPort
from modules.movimientos.application.services.ajustador_de_stock import AjustadorDeStockService
from modules.movimientos.domain.entities.movimiento import ItemMovimiento, Movimiento
from modules.movimientos.domain.errors import MovimientoUbicacionNoEspecificadaError
from shared.application.persistence.unit_of_work import UnitOfWorkFactory, UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona

PREFIJO_REMISION = "RM"


class RegistrarSalidaPorMercadoService:
    """Registra una salida a partir de un mercado predefinido (catálogo de
    kit, ver `mercados_predefinidos`). A diferencia del legacy:
    - la ubicación de origen es explícita (un valor por producto del kit en el
      request — cada producto puede vivir en una ubicación física distinta),
      no una heurística de "la primera ubicación con stock suficiente" (esa
      heurística es la que llamaba a `crud.get_ubicaciones_producto`,
      función inexistente — bug real del legacy);
    - genera un único `Movimiento` con todos los productos embebidos (mismo
      patrón que `ConfirmarReservaKitService`), no uno por producto;
    - no genera el PDF automáticamente — se pide después vía
      `GET /movimientos/{id}/comprobante`, igual que cualquier otra salida.
    """

    def __init__(
        self,
        mercado_predefinido_repository: MercadoPredefinidoRepositoryPort,
        movimiento_repository: MovimientoRepositoryPort,
        ajustador_de_stock: AjustadorDeStockService,
        generador_secuencial: GeneradorSecuencialPort,
        unit_of_work_factory: UnitOfWorkFactory,
    ):
        self._mercado_predefinido_repository = mercado_predefinido_repository
        self._movimiento_repository = movimiento_repository
        self._ajustador_de_stock = ajustador_de_stock
        self._generador_secuencial = generador_secuencial
        self._unit_of_work_factory = unit_of_work_factory

    async def ejecutar(
        self, entrada: RegistrarSalidaPorMercadoInput, creado_por: AuditPersona
    ) -> Movimiento:
        """Raises:
        MercadoNoEncontradoError: no existe un mercado predefinido con ese nombre.
        ProductoNoEncontradoError: algún producto del mercado ya no existe en el catálogo.
        MovimientoUbicacionNoEspecificadaError: la request no indica la ubicación de
            origen de algún producto del mercado (cada producto puede vivir en una
            ubicación física distinta — no hay una única ubicación válida para todos).
        MovimientoUbicacionNoEncontradaError: la ubicación indicada no existe para algún producto.
        MovimientoStockInsuficienteError: stock físico insuficiente en la ubicación indicada.
        """
        mercado = await self._mercado_predefinido_repository.obtener_por_nombre(
            entrada.mercado_nombre
        )
        if mercado is None:
            raise MercadoNoEncontradoError(entrada.mercado_nombre)

        ubicaciones_por_producto = {item.producto_codigo: item.ubicacion for item in entrada.productos}

        async with self._unit_of_work_factory() as uow:
            remision = await self._generador_secuencial.siguiente(
                nombre="remision", prefijo=PREFIJO_REMISION, uow=uow
            )

            items_movimiento = [
                await self._descontar_item(
                    producto_kit.producto_id,
                    producto_kit.cantidad * entrada.cantidad,
                    self._resolver_ubicacion(producto_kit.producto_id, ubicaciones_por_producto),
                    creado_por,
                    uow,
                )
                for producto_kit in mercado.productos
            ]

            movimiento = Movimiento.registrar_mercado(
                nombre_mercado=mercado.nombre,
                productos=items_movimiento,
                cantidad=entrada.cantidad,
                cliente_destino=entrada.cliente_destino,
                notas=entrada.notas,
                referencia=entrada.referencia,
                remision=remision,
                creado_por=creado_por,
            )
            return await self._movimiento_repository.crear(movimiento, uow=uow)

    @staticmethod
    def _resolver_ubicacion(producto_codigo: str, ubicaciones_por_producto: dict[str, str]) -> str:
        ubicacion = ubicaciones_por_producto.get(producto_codigo)
        if not ubicacion:
            raise MovimientoUbicacionNoEspecificadaError(producto_codigo)
        return ubicacion

    async def _descontar_item(
        self,
        producto_codigo: str,
        cantidad: int,
        ubicacion: str,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort,
    ) -> ItemMovimiento:
        producto = await self._ajustador_de_stock.descontar(
            producto_codigo, ubicacion, cantidad, creado_por, uow
        )
        return ItemMovimiento(
            producto_codigo=producto_codigo,
            producto_nombre=producto.nombre,
            cantidad=cantidad,
            ubicacion=ubicacion,
        )
