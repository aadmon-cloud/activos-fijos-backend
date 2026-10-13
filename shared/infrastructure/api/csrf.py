from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.settings import settings
from shared.application.user_auth.errors import CabeceraCsrfFaltanteError

CABECERA_CSRF = "X-Requested-With"
VALOR_CSRF = "XMLHttpRequest"
METODOS_QUE_MODIFICAN_ESTADO = {"POST", "PUT", "PATCH", "DELETE"}


class CsrfHeaderMiddleware(BaseHTTPMiddleware):
    """Exige una cabecera personalizada cuando la peticion que modifica estado
    viaja con la cookie de sesion. Un formulario cross-site no puede enviarla."""

    async def dispatch(self, request: Request, call_next):
        if (
            request.method in METODOS_QUE_MODIFICAN_ESTADO
            and request.cookies.get(settings.COOKIE_NAME)
            and request.headers.get(CABECERA_CSRF) != VALOR_CSRF
        ):
            error = CabeceraCsrfFaltanteError()
            return JSONResponse(
                status_code=403,
                content={
                    "status": "error",
                    "code": error.code,
                    "message": error.message,
                    "category": error.category.value,
                    "path": request.url.path,
                    "metadata": error.details,
                },
            )

        return await call_next(request)
