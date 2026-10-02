from __future__ import annotations

from datetime import datetime

from shared.domain.entities.base import BaseDomainEntity


class AuditPersona(BaseDomainEntity):
    """Quien realizó una acción de auditoría, con el nombre desnormalizado."""

    id_persona: str
    nombre: str
    fecha: datetime
