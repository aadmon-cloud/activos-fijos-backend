from abc import ABC, abstractmethod

from modules.productos.domain.entities.producto import Producto
from shared.application.persistence.unit_of_work import UnitOfWorkPort


class ProductoRepositoryPort(ABC):
    @abstractmethod
    async def obtener_por_codigo(self, codigo: str) -> Producto | None:
        """Return the product with this código, or None if it does not exist."""

    @abstractmethod
    async def existe_por_codigo(self, codigo: str) -> bool:
        """Return whether a product with this código already exists."""

    @abstractmethod
    async def crear(self, producto: Producto) -> Producto:
        """Persist a new product and return it with its assigned id."""

    @abstractmethod
    async def actualizar(
        self, producto: Producto, uow: UnitOfWorkPort | None = None
    ) -> Producto:
        """Persist the updated state of an existing product.

        `uow`: cuando se provee, la escritura participa de esa transacción
        (ej. `ubicaciones` recalculando `stock_actual` junto con su propia
        escritura). Sin `uow`, es una escritura suelta como cualquier otra.
        """

    @abstractmethod
    async def eliminar(self, codigo: str) -> bool:
        """Delete the product with this código. Return whether a document was deleted."""

    @abstractmethod
    async def listar_paginado(self, pagina: int, limite: int) -> tuple[list[Producto], int]:
        """Return a paginated slice of products and the total number of records."""

    @abstractmethod
    async def buscar_por_texto(self, texto: str) -> list[Producto]:
        """Return products whose name matches this text search."""

    @abstractmethod
    async def listar_bajo_stock(self) -> list[Producto]:
        """Return every product whose stock_actual is below its stock_minimo."""

    @abstractmethod
    async def calcular_valor_total(self) -> float:
        """Return sum(stock_actual * precio_unitario) across every product."""
