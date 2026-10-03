from dataclasses import dataclass, field
from typing import Any


@dataclass
class IdentidadAutenticada:
    email: str
    claims: dict[str, Any] = field(default_factory=dict)
