from __future__ import annotations

from shared.domain.entities.audit_persona import AuditPersona
from shared.domain.entities.base import BaseDomainEntity

from modules.mercados_predefinidos.domain.errors import MercadoProductosVacioError


class ProductoKit(BaseDomainEntity):
    producto_id: str
    cantidad: int
    producto_nombre: str


class MercadoPredefinido(BaseDomainEntity):
    id: str | None = None
    nombre: str
    descripcion: str | None = None
    productos: list[ProductoKit]
    activo: bool = True
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None = None

    @classmethod
    def crear(
        cls,
        nombre: str,
        descripcion: str | None,
        productos: list[ProductoKit],
        creado_por: AuditPersona,
    ) -> "MercadoPredefinido":
        """`productos` llega ya resuelto (con `producto_nombre` correcto) — la
        entidad no conoce el repositorio de productos."""
        if not productos:
            raise MercadoProductosVacioError()
        return cls(
            id=None,
            nombre=nombre.strip(),
            descripcion=descripcion.strip() if descripcion else None,
            productos=productos,
            activo=True,
            creado_por=creado_por,
        )

    def actualizar(
        self,
        actualizado_por: AuditPersona,
        descripcion: str | None = None,
        productos: list[ProductoKit] | None = None,
        activo: bool | None = None,
    ) -> "MercadoPredefinido":
        """Update parcial. `nombre` no es editable (es la clave de búsqueda)."""
        cambios: dict = {"actualizado_por": actualizado_por}
        if descripcion is not None:
            cambios["descripcion"] = descripcion.strip()
        if productos is not None:
            if not productos:
                raise MercadoProductosVacioError()
            cambios["productos"] = productos
        if activo is not None:
            cambios["activo"] = activo
        return self.model_copy(update=cambios)
