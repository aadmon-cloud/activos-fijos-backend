from __future__ import annotations

from datetime import datetime

from shared.domain.entities.audit_persona import AuditPersona
from shared.domain.entities.base import BaseDomainEntity

from modules.reservas.domain.errors import ReservaSinItemsError


class ItemReserva(BaseDomainEntity):
    producto_codigo: str
    ubicacion: str
    cantidad: int


class Reserva(BaseDomainEntity):
    id: str | None = None
    session_id: str
    items: list[ItemReserva]
    datos_adicionales: dict | None = None
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None = None
    ultima_actividad: datetime

    @classmethod
    def crear(
        cls,
        session_id: str,
        items: list[ItemReserva],
        datos_adicionales: dict | None,
        creado_por: AuditPersona,
    ) -> "Reserva":
        if not items:
            raise ReservaSinItemsError()
        return cls(
            id=None,
            session_id=session_id,
            items=items,
            datos_adicionales=datos_adicionales,
            creado_por=creado_por,
            ultima_actividad=creado_por.fecha,
        )

    def aplicar_ajuste(
        self,
        producto_codigo: str,
        ubicacion: str,
        diferencia: int,
        actualizado_por: AuditPersona,
    ) -> "Reserva":
        """Aplica un delta con signo a un item, identificado por
        (producto_codigo, ubicacion). Crea el item si `diferencia > 0` y no
        existía; lo elimina si la cantidad resultante es `<= 0`; no hace nada
        si se intenta restar de un item que no existe (mismo criterio que el
        legacy, que solo lo registraba como advertencia)."""
        items_por_clave = {(i.producto_codigo, i.ubicacion): i for i in self.items}
        clave = (producto_codigo, ubicacion)

        if clave in items_por_clave:
            nueva_cantidad = items_por_clave[clave].cantidad + diferencia
            if nueva_cantidad > 0:
                items_por_clave[clave] = ItemReserva(
                    producto_codigo=producto_codigo, ubicacion=ubicacion, cantidad=nueva_cantidad
                )
            else:
                del items_por_clave[clave]
        elif diferencia > 0:
            items_por_clave[clave] = ItemReserva(
                producto_codigo=producto_codigo, ubicacion=ubicacion, cantidad=diferencia
            )

        return self.model_copy(
            update={
                "items": list(items_por_clave.values()),
                "actualizado_por": actualizado_por,
                "ultima_actividad": actualizado_por.fecha,
            }
        )

    @property
    def sin_items(self) -> bool:
        return len(self.items) == 0
