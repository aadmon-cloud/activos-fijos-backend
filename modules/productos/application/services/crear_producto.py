import secrets
from datetime import UTC, datetime

from modules.productos.application.dto.crear_producto import CrearProductoInput
from modules.productos.application.ports.producto_repository import ProductoRepositoryPort
from modules.productos.domain.entities.producto import Producto
from modules.productos.domain.errors import ProductoCodigoDuplicadoError
from shared.domain.entities.audit_persona import AuditPersona


class CrearProductoService:
    def __init__(self, producto_repository: ProductoRepositoryPort):
        self._producto_repository = producto_repository

    async def ejecutar(self, entrada: CrearProductoInput, creado_por: AuditPersona) -> Producto:
        """Crea un producto. Si no se provee `codigo`, se autogenera.

        Raises:
            ProductoCodigoDuplicadoError: el código (provisto o autogenerado) ya existe.
        """
        codigo = entrada.codigo.strip() if entrada.codigo else _generar_codigo()
        if await self._producto_repository.existe_por_codigo(codigo):
            raise ProductoCodigoDuplicadoError(codigo)

        nuevo_producto = Producto.crear(
            codigo=codigo,
            nombre=entrada.nombre,
            descripcion=entrada.descripcion,
            categoria=entrada.categoria,
            stock_minimo=entrada.stock_minimo,
            precio_unitario=entrada.precio_unitario,
            creado_por=creado_por,
        )
        return await self._producto_repository.crear(nuevo_producto)


def _generar_codigo() -> str:
    fecha = datetime.now(UTC).strftime("%Y%m%d")
    sufijo = secrets.token_hex(3).upper()
    return f"PROD-{fecha}-{sufijo}"
