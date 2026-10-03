from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class BaseDomainEntity:
    """Base para entidades de dominio puras, sin dependencias externas."""
