from fastapi import FastAPI
from fastapi.testclient import TestClient

from shared.infrastructure.api.csrf import CsrfHeaderMiddleware


def _cliente() -> TestClient:
    app = FastAPI()
    app.add_middleware(CsrfHeaderMiddleware)

    @app.post("/api/x")
    async def crear():
        return {"status": "success"}

    @app.get("/api/x")
    async def leer():
        return {"status": "success"}

    return TestClient(app)


def test_rechaza_con_403_un_post_con_cookie_de_sesion_sin_cabecera_csrf():
    cliente = _cliente()
    cliente.cookies.set("access_token", "t")

    respuesta = cliente.post("/api/x")

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "AUTH-004"


def test_permite_un_post_con_cookie_y_cabecera_csrf():
    cliente = _cliente()
    cliente.cookies.set("access_token", "t")

    respuesta = cliente.post("/api/x", headers={"X-Requested-With": "XMLHttpRequest"})

    assert respuesta.status_code == 200


def test_permite_un_post_sin_cookie_de_sesion():
    respuesta = _cliente().post("/api/x")

    assert respuesta.status_code == 200


def test_no_exige_cabecera_en_metodos_de_solo_lectura():
    cliente = _cliente()
    cliente.cookies.set("access_token", "t")

    assert cliente.get("/api/x").status_code == 200
