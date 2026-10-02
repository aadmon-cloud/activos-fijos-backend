from abc import ABC, abstractmethod

from shared.application.persistence.unit_of_work import UnitOfWorkPort
from shared.domain.entities.audit_persona import AuditPersona


class RegistradorDeMovimientosPort(ABC):
    """Puerto que posee `ubicaciones` para notificar eventos de bitácora a
    `movimientos`, sin depender de su código concreto (inversión de
    dependencias — evita el ciclo `movimientos↔ubicaciones`, ver
    MIGRATION_PLAN.md, incremento 5 de `movimientos`). El adaptador concreto
    vive en `modules/movimientos/infrastructure/`."""

    @abstractmethod
    async def registrar_creacion_ubicacion(
        self,
        producto_codigo: str,
        ubicacion: str,
        cantidad: int,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort | None = None,
    ) -> None:
        """Deja constancia de que se creó esta ubicación con este stock inicial."""

    @abstractmethod
    async def registrar_transferencia_stock(
        self,
        producto_codigo: str,
        ubicacion_origen: str,
        ubicacion_destino: str,
        cantidad: int,
        creado_por: AuditPersona,
        uow: UnitOfWorkPort | None = None,
    ) -> None:
        """Deja constancia de que se transfirió stock entre dos ubicaciones."""
