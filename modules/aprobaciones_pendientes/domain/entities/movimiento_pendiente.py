from __future__ import annotations

from typing import Literal

from shared.domain.entities.audit_persona import AuditPersona
from shared.domain.entities.base import BaseDomainEntity

from modules.aprobaciones_pendientes.domain.errors import MovimientoPendienteYaConfirmadoError

TipoPropuesto = Literal["entrada", "entrada_multiple", "salida", "salida_multiple"]
EstadoMovimientoPendiente = Literal["pendiente", "confirmada"]


class MovimientoPendiente(BaseDomainEntity):
    """Propuesta de un usuario no-super_admin de registrar una entrada o
    salida — queda en estado "pendiente" hasta que un super_admin la
    confirme (aplica el movimiento real) o alguien autorizado la elimine.

    `payload` guarda los mismos campos que el `Input` DTO de `movimientos`
    correspondiente a `tipo_propuesto` (validado en la capa de aplicación,
    no acá — mismo criterio que `reservas.datos_adicionales`)."""

    id: str | None = None
    tipo_propuesto: TipoPropuesto
    payload: dict
    estado: EstadoMovimientoPendiente
    movimiento_id: str | None = None
    creado_por: AuditPersona
    confirmado_por: AuditPersona | None = None

    @classmethod
    def proponer(
        cls,
        tipo_propuesto: TipoPropuesto,
        payload: dict,
        creado_por: AuditPersona,
    ) -> "MovimientoPendiente":
        return cls(
            id=None,
            tipo_propuesto=tipo_propuesto,
            payload=payload,
            estado="pendiente",
            movimiento_id=None,
            creado_por=creado_por,
            confirmado_por=None,
        )

    def confirmar(
        self, movimiento_id: str, confirmado_por: AuditPersona
    ) -> "MovimientoPendiente":
        self._exigir_pendiente()
        return self.model_copy(
            update={
                "estado": "confirmada",
                "movimiento_id": movimiento_id,
                "confirmado_por": confirmado_por,
            }
        )

    def exigir_eliminable(self) -> None:
        self._exigir_pendiente()

    def pertenece_a(self, id_persona: str) -> bool:
        return self.creado_por.id_persona == id_persona

    def _exigir_pendiente(self) -> None:
        if self.estado != "pendiente":
            raise MovimientoPendienteYaConfirmadoError(self.id or "")
