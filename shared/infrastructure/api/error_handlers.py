import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from shared.domain.errors import DomainError, ErrorCategory

logger = logging.getLogger(__name__)

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
    # Fallback de seguridad: hoy los 8 miembros de ErrorCategory estan cubiertos,
    # pero esto evita un KeyError si en el futuro se agrega un miembro nuevo sin
    # actualizar este mapeo.
    return int(STATUS_BY_CATEGORY.get(error.category, HTTPStatus.INTERNAL_SERVER_ERROR))


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _manejar_domain_error(request: Request, exc: DomainError) -> JSONResponse:
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
    async def _manejar_excepcion_no_controlada(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Excepcion no controlada en %s", request.url.path)
        return JSONResponse(
            status_code=int(HTTPStatus.INTERNAL_SERVER_ERROR),
            content={
                "status": "error",
                "code": "GEN-500",
                "message": "Ocurrio un error interno no controlado.",
                "path": request.url.path,
            },
        )
