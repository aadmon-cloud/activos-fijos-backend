from fastapi import Response

from config.settings import settings


def establecer_cookie_sesion(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/api",
        domain=settings.COOKIE_DOMAIN or None,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )


def eliminar_cookie_sesion(response: Response) -> None:
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/api",
        domain=settings.COOKIE_DOMAIN or None,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )
