from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MongoIndexDefinition:
    """Declarative description of a MongoDB index."""

    name: str
    keys: list[tuple[str, int]]
    unique: bool = False
    sparse: bool = False
    partial_filter_expression: dict[str, Any] | None = None
    expire_after_seconds: int | None = None

    def to_driver_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "unique": self.unique,
            "sparse": self.sparse,
        }
        if self.partial_filter_expression:
            kwargs["partialFilterExpression"] = self.partial_filter_expression
        if self.expire_after_seconds is not None:
            kwargs["expireAfterSeconds"] = self.expire_after_seconds
        return kwargs


@dataclass(frozen=True)
class MongoCollectionDefinition:
    """Declarative description of a MongoDB collection contract."""

    name: str
    validator: dict[str, Any]
    indexes: list[MongoIndexDefinition] = field(default_factory=list)
    validation_level: str = "strict"
    validation_action: str = "error"

    def to_create_collection_kwargs(self) -> dict[str, Any]:
        return {
            "validator": self.validator,
            "validationLevel": self.validation_level,
            "validationAction": self.validation_action,
        }
