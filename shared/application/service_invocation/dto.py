from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConfiguracionServicioExterno:
    nombre: str
    url_base: str
    audiencia_resuelta: str | None = None
    requiere_autenticacion: bool = True
    cabeceras_extra: dict[str, str] = field(default_factory=dict)
    tiempo_espera_segundos: float = 10.0


@dataclass
class SolicitudServicioExterno:
    ruta: str
    metodo: str = "GET"
    cuerpo_json: Any | None = None
    parametros_query: dict[str, Any] | None = None
    cabeceras: dict[str, str] = field(default_factory=dict)
    tiempo_espera_segundos: float | None = None
