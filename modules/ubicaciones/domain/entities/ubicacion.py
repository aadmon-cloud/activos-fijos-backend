from __future__ import annotations

from shared.domain.entities.audit_persona import AuditPersona
from shared.domain.entities.base import BaseDomainEntity


class Ubicacion(BaseDomainEntity):
    id: str | None = None
    producto_codigo: str
    ubicacion: str
    stock_fisico: int = 0
    stock_reservado: int = 0
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None = None

    @classmethod
    def crear(
        cls,
        producto_codigo: str,
        ubicacion: str,
        stock_fisico: int,
        creado_por: AuditPersona,
    ) -> "Ubicacion":
        return cls(
            id=None,
            producto_codigo=producto_codigo,
            ubicacion=ubicacion.strip(),
            stock_fisico=stock_fisico,
            stock_reservado=0,
            creado_por=creado_por,
        )

    def actualizar_stock_fisico(
        self, nuevo_stock_fisico: int, actualizado_por: AuditPersona
    ) -> "Ubicacion":
        return self.model_copy(
            update={"stock_fisico": nuevo_stock_fisico, "actualizado_por": actualizado_por}
        )

    @property
    def stock_disponible(self) -> int:
        return max(0, self.stock_fisico - self.stock_reservado)
