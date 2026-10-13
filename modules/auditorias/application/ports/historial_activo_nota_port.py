from abc import ABC, abstractmethod

from shared.domain.entities.audit import AuditPersona


class HistorialActivoNotaPort(ABC):
    """Escribe directo en la coleccion activos_historial (por nombre, sin importar codigo de
    modules.activos), igual que ActivoResumenPort hace para leerla."""

    @abstractmethod
    async def registrar_nota(
        self, activo_id: str, nota: str, auditoria_id: str, auditor: AuditPersona
    ) -> None: ...
