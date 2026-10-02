from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    VALIDATION = "validation"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    BUSINESS_RULE = "business_rule"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    INTEGRATION = "integration"
    INTERNAL = "internal"


class DomainError(Exception):
    """Base error for the inner layers of the application."""

    def __init__(
        self,
        message: str,
        code: str = "DOMAIN_ERROR",
        category: ErrorCategory = ErrorCategory.BUSINESS_RULE,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.details = details or {}
