from __future__ import annotations

from typing import Any

from shared.domain.errors import DomainError, ErrorCategory


class ApplicationError(DomainError):
    """Base error for orchestration and use-case concerns."""

    def __init__(
        self,
        message: str,
        code: str = "APPLICATION_ERROR",
        category: ErrorCategory = ErrorCategory.INTERNAL,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code=code,
            category=category,
            details=details,
        )
