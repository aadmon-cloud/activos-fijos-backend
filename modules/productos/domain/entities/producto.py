from __future__ import annotations

from shared.domain.entities.audit_persona import AuditPersona
from shared.domain.entities.base import BaseDomainEntity


class Producto(BaseDomainEntity):
    id: str | None = None
    codigo: str
    nombre: str
    descripcion: str | None = None
    categoria: str | None = None
    stock_minimo: int = 0
    stock_actual: int = 0
    precio_unitario: float = 0.0
    imagen_url: str | None = None
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None = None

    @classmethod
    def crear(
        cls,
        codigo: str,
        nombre: str,
        descripcion: str | None,
        categoria: str | None,
        stock_minimo: int,
        precio_unitario: float,
        creado_por: AuditPersona,
    ) -> "Producto":
        """`codigo` llega ya resuelto (provisto o autogenerado) y verificado como
        único por el service — la entidad no conoce el repositorio."""
        return cls(
            id=None,
            codigo=codigo,
            nombre=nombre.strip(),
            descripcion=descripcion.strip() if descripcion else None,
            categoria=categoria.strip() if categoria else None,
            stock_minimo=stock_minimo,
            stock_actual=0,
            precio_unitario=precio_unitario,
            imagen_url=None,
            creado_por=creado_por,
        )

    def actualizar(
        self,
        actualizado_por: AuditPersona,
        nombre: str | None = None,
        descripcion: str | None = None,
        categoria: str | None = None,
        stock_minimo: int | None = None,
        precio_unitario: float | None = None,
    ) -> "Producto":
        """Update parcial: solo se aplican los campos que vienen distintos de None.

        No permite tocar `codigo` (identificador estable), `stock_actual`
        (denormalizado, propiedad de `ubicaciones`/`movimientos`) ni `imagen_url`
        (incremento futuro con su propio service dedicado).
        """
        cambios: dict = {"actualizado_por": actualizado_por}
        if nombre is not None:
            cambios["nombre"] = nombre.strip()
        if descripcion is not None:
            cambios["descripcion"] = descripcion.strip()
        if categoria is not None:
            cambios["categoria"] = categoria.strip()
        if stock_minimo is not None:
            cambios["stock_minimo"] = stock_minimo
        if precio_unitario is not None:
            cambios["precio_unitario"] = precio_unitario
        return self.model_copy(update=cambios)

    def recalcular_stock(self, nuevo_stock_actual: int) -> "Producto":
        """Proyección recalculada desde `ubicaciones` (suma de `stock_fisico`) —
        a diferencia de `actualizar()`, no es una edición de usuario."""
        return self.model_copy(update={"stock_actual": nuevo_stock_actual})
