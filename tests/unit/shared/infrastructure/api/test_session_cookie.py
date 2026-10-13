from fastapi import Response

from shared.infrastructure.api.session_cookie import (
    eliminar_cookie_sesion,
    establecer_cookie_sesion,
)


def test_establecer_cookie_sesion_usa_atributos_seguros():
    response = Response()

    establecer_cookie_sesion(response, "jwt")

    cookie = response.headers["set-cookie"].lower()
    assert "access_token=jwt" in cookie
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "path=/api" in cookie


def test_eliminar_cookie_sesion_la_expira():
    response = Response()

    eliminar_cookie_sesion(response)

    assert "max-age=0" in response.headers["set-cookie"].lower()
