from dataclasses import dataclass

from modules.solicitudes.domain.entities import EstadoSolicitud, TipoSolicitud

# Estados del ciclo de vida del activo, como texto: solicitudes no importa el codigo del modulo activos.
# Deben coincidir con `EstadoCicloVida` de modules/activos/domain/entities.py.
ACTIVO_DISPONIBLE = "disponible"
ACTIVO_EN_MANTENIMIENTO = "en_mantenimiento"
ACTIVO_PERDIDO = "perdido"
ACTIVO_DANADO = "danado"

ETIQUETAS_ESTADO_ACTIVO = {
    "disponible": "Disponible",
    "prestado": "Prestado",
    "en_mantenimiento": "En mantenimiento",
    "dado_de_baja": "Dado de baja",
    "perdido": "Perdido",
    "danado": "Dañado",
}


@dataclass(frozen=True)
class EfectoEnActivo:
    """Estado al que pasa el activo cuando la solicitud llega a cierto estado."""

    estado_destino: str

    # Si se indica, el efecto solo aplica cuando el activo esta en ese estado (para no deshacer un
    # cambio posterior hecho a mano, p. ej. un activo dado de baja mientras se mantenia).
    solo_si_actual: str | None = None


_EFECTOS: dict[tuple[TipoSolicitud, EstadoSolicitud], EfectoEnActivo] = {
    (TipoSolicitud.MANTENIMIENTO, EstadoSolicitud.EN_PROCESO): EfectoEnActivo(ACTIVO_EN_MANTENIMIENTO),
    (TipoSolicitud.MANTENIMIENTO, EstadoSolicitud.RESUELTA): EfectoEnActivo(
        ACTIVO_DISPONIBLE, solo_si_actual=ACTIVO_EN_MANTENIMIENTO
    ),
    (TipoSolicitud.REPORTE_DANO, EstadoSolicitud.EN_PROCESO): EfectoEnActivo(ACTIVO_DANADO),
    (TipoSolicitud.REPORTE_PERDIDA, EstadoSolicitud.EN_PROCESO): EfectoEnActivo(ACTIVO_PERDIDO),
}


def efecto_en_activo(tipo: TipoSolicitud, estado_nuevo: EstadoSolicitud) -> EfectoEnActivo | None:
    """Efecto sobre el activo de llevar una solicitud de este tipo a `estado_nuevo`; None si no hay."""
    return _EFECTOS.get((tipo, estado_nuevo))
