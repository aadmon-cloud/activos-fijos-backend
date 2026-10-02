from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.domain.errors import DomainError, ErrorCategory

STATUS_BY_CATEGORY = {
    ErrorCategory.VALIDATION: HTTPStatus.BAD_REQUEST,
    ErrorCategory.NOT_FOUND: HTTPStatus.NOT_FOUND,
    ErrorCategory.CONFLICT: HTTPStatus.CONFLICT,
    ErrorCategory.BUSINESS_RULE: HTTPStatus.UNPROCESSABLE_ENTITY,
    ErrorCategory.UNAUTHORIZED: HTTPStatus.UNAUTHORIZED,
    ErrorCategory.FORBIDDEN: HTTPStatus.FORBIDDEN,
    ErrorCategory.INTEGRATION: HTTPStatus.BAD_GATEWAY,
    ErrorCategory.INTERNAL: HTTPStatus.INTERNAL_SERVER_ERROR,
}


def _resolver_status_http(error: DomainError) -> int:
    return int(STATUS_BY_CATEGORY.get(error.category, HTTPStatus.INTERNAL_SERVER_ERROR))


def register_error_handlers(app: FastAPI):
    @app.exception_handler(DomainError)
    async def domain_exception_handler(request: Request, exc: DomainError):
        return JSONResponse(
            status_code=_resolver_status_http(exc),
            content={
                "status": "error",
                "code": exc.code,
                "message": exc.message,
                "category": exc.category.value,
                "path": request.url.path,
                "metadata": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, _: Exception):
        return JSONResponse(
            status_code=int(HTTPStatus.INTERNAL_SERVER_ERROR),
            content={
                "status": "error",
                "code": "GEN-500",
                "message": "Ocurrio un error interno no controlado.",
                "path": request.url.path,
            },
        )
