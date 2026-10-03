from dataclasses import replace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from modules.catalogos.application.ports.area_repository import AreaRepositoryPort
from modules.catalogos.application.ports.categoria_repository import CategoriaRepositoryPort
from modules.catalogos.application.ports.condicion_repository import CondicionRepositoryPort
from modules.catalogos.application.ports.lugar_repository import LugarRepositoryPort
from modules.catalogos.application.ports.sede_repository import SedeRepositoryPort
from modules.catalogos.application.services.actualizar_area import ActualizarAreaService
from modules.catalogos.application.services.actualizar_categoria import (
    ActualizarCategoriaService,
)
from modules.catalogos.application.services.actualizar_condicion import (
    ActualizarCondicionService,
)
from modules.catalogos.application.services.actualizar_lugar import ActualizarLugarService
from modules.catalogos.application.services.actualizar_sede import ActualizarSedeService
from modules.catalogos.application.services.crear_area import CrearAreaService
from modules.catalogos.application.services.crear_categoria import CrearCategoriaService
from modules.catalogos.application.services.crear_condicion import CrearCondicionService
from modules.catalogos.application.services.crear_lugar import CrearLugarService
from modules.catalogos.application.services.crear_sede import CrearSedeService
from modules.catalogos.application.services.eliminar_area import EliminarAreaService
from modules.catalogos.application.services.eliminar_categoria import EliminarCategoriaService
from modules.catalogos.application.services.eliminar_condicion import EliminarCondicionService
from modules.catalogos.application.services.eliminar_lugar import EliminarLugarService
from modules.catalogos.application.services.eliminar_sede import EliminarSedeService
from modules.catalogos.application.services.listar_areas import ListarAreasService
from modules.catalogos.application.services.listar_categorias import ListarCategoriasService
from modules.catalogos.application.services.listar_condiciones import ListarCondicionesService
from modules.catalogos.application.services.listar_lugares import ListarLugaresService
from modules.catalogos.application.services.listar_sedes import ListarSedesService
from modules.catalogos.application.services.obtener_area import ObtenerAreaService
from modules.catalogos.application.services.obtener_categoria import ObtenerCategoriaService
from modules.catalogos.application.services.obtener_condicion import ObtenerCondicionService
from modules.catalogos.application.services.obtener_lugar import ObtenerLugarService
from modules.catalogos.application.services.obtener_sede import ObtenerSedeService
from modules.catalogos.domain.entities import Area, Categoria, Condicion, Lugar, Sede
from modules.catalogos.infrastructure.api.area_routes import router as area_router
from modules.catalogos.infrastructure.api.categoria_routes import router as categoria_router
from modules.catalogos.infrastructure.api.condicion_routes import router as condicion_router
from modules.catalogos.infrastructure.api.lugar_routes import router as lugar_router
from modules.catalogos.infrastructure.api.sede_routes import router as sede_router
from modules.catalogos.infrastructure.api.dependencies import (
    get_actualizar_area_service,
    get_actualizar_categoria_service,
    get_actualizar_condicion_service,
    get_actualizar_lugar_service,
    get_actualizar_sede_service,
    get_crear_area_service,
    get_crear_categoria_service,
    get_crear_condicion_service,
    get_crear_lugar_service,
    get_crear_sede_service,
    get_eliminar_area_service,
    get_eliminar_categoria_service,
    get_eliminar_condicion_service,
    get_eliminar_lugar_service,
    get_eliminar_sede_service,
    get_listar_areas_service,
    get_listar_categorias_service,
    get_listar_condiciones_service,
    get_listar_lugares_service,
    get_listar_sedes_service,
    get_obtener_area_service,
    get_obtener_categoria_service,
    get_obtener_condicion_service,
    get_obtener_lugar_service,
    get_obtener_sede_service,
)
from shared.application.user_auth.dto import IdentidadUsuarioAutenticada
from shared.infrastructure.api.dependencies.user_authentication import (
    requiere_usuario_autenticado,
)
from shared.infrastructure.api.error_handlers import register_error_handlers


class _RepositorioAreaEnMemoria(AreaRepositoryPort):
    def __init__(self):
        self._items: dict[str, Area] = {}
        self._contador = 0

    async def guardar(self, area: Area) -> Area:
        if area.id is None:
            self._contador += 1
            area = replace(area, id=str(self._contador))
        self._items[area.id] = area
        return area

    async def obtener_por_id(self, id_area: str):
        return self._items.get(id_area)

    async def obtener_por_nombre(self, nombre: str):
        return next((a for a in self._items.values() if a.nombre == nombre), None)

    async def listar(self):
        return list(self._items.values())

    async def eliminar(self, id_area: str) -> None:
        self._items.pop(id_area, None)


class _RepositorioCategoriaEnMemoria(CategoriaRepositoryPort):
    def __init__(self):
        self._items: dict[str, Categoria] = {}
        self._contador = 0

    async def guardar(self, categoria: Categoria) -> Categoria:
        if categoria.id is None:
            self._contador += 1
            categoria = replace(categoria, id=str(self._contador))
        self._items[categoria.id] = categoria
        return categoria

    async def obtener_por_id(self, id_categoria: str):
        return self._items.get(id_categoria)

    async def obtener_por_nombre(self, nombre: str):
        return next((c for c in self._items.values() if c.nombre == nombre), None)

    async def listar(self):
        return list(self._items.values())

    async def eliminar(self, id_categoria: str) -> None:
        self._items.pop(id_categoria, None)


class _RepositorioCondicionEnMemoria(CondicionRepositoryPort):
    def __init__(self):
        self._items: dict[str, Condicion] = {}
        self._contador = 0

    async def guardar(self, condicion: Condicion) -> Condicion:
        if condicion.id is None:
            self._contador += 1
            condicion = replace(condicion, id=str(self._contador))
        self._items[condicion.id] = condicion
        return condicion

    async def obtener_por_id(self, id_condicion: str):
        return self._items.get(id_condicion)

    async def obtener_por_nombre(self, nombre: str):
        return next((c for c in self._items.values() if c.nombre == nombre), None)

    async def listar(self):
        return list(self._items.values())

    async def eliminar(self, id_condicion: str) -> None:
        self._items.pop(id_condicion, None)


class _RepositorioSedeEnMemoria(SedeRepositoryPort):
    def __init__(self):
        self._items: dict[str, Sede] = {}
        self._contador = 0

    async def guardar(self, sede: Sede) -> Sede:
        if sede.id is None:
            self._contador += 1
            sede = replace(sede, id=str(self._contador))
        self._items[sede.id] = sede
        return sede

    async def obtener_por_id(self, id_sede: str):
        return self._items.get(id_sede)

    async def obtener_por_nombre(self, nombre: str):
        return next((s for s in self._items.values() if s.nombre == nombre), None)

    async def listar(self):
        return list(self._items.values())

    async def eliminar(self, id_sede: str) -> None:
        self._items.pop(id_sede, None)


class _RepositorioLugarEnMemoria(LugarRepositoryPort):
    def __init__(self):
        self._items: dict[str, Lugar] = {}
        self._contador = 0

    async def guardar(self, lugar: Lugar) -> Lugar:
        if lugar.id is None:
            self._contador += 1
            lugar = replace(lugar, id=str(self._contador))
        self._items[lugar.id] = lugar
        return lugar

    async def obtener_por_id(self, id_lugar: str):
        return self._items.get(id_lugar)

    async def obtener_por_nombre_y_sede(self, sede_id: str, nombre: str):
        return next(
            (l for l in self._items.values() if l.sede_id == sede_id and l.nombre == nombre),
            None,
        )

    async def listar(self, sede_id: str | None):
        valores = list(self._items.values())
        if sede_id:
            valores = [l for l in valores if l.sede_id == sede_id]
        return valores

    async def existe_alguno_con_sede(self, sede_id: str) -> bool:
        return any(l.sede_id == sede_id for l in self._items.values())

    async def eliminar(self, id_lugar: str) -> None:
        self._items.pop(id_lugar, None)


class _VerificadorUsoEnActivosFalso:
    async def area_esta_en_uso(self, area_id: str) -> bool:
        return False

    async def categoria_esta_en_uso(self, categoria_id: str) -> bool:
        return False

    async def condicion_esta_en_uso(self, condicion_id: str) -> bool:
        return False

    async def lugar_esta_en_uso(self, lugar_id: str) -> bool:
        return False


def _crear_cliente_de_prueba():
    app = FastAPI()
    register_error_handlers(app)
    app.include_router(area_router)
    app.include_router(categoria_router)
    app.include_router(condicion_router)
    app.include_router(sede_router)
    app.include_router(lugar_router)

    repo_area = _RepositorioAreaEnMemoria()
    repo_categoria = _RepositorioCategoriaEnMemoria()
    repo_condicion = _RepositorioCondicionEnMemoria()
    repo_sede = _RepositorioSedeEnMemoria()
    repo_lugar = _RepositorioLugarEnMemoria()
    verificador_uso = _VerificadorUsoEnActivosFalso()

    app.dependency_overrides[get_crear_area_service] = lambda: CrearAreaService(repo_area)
    app.dependency_overrides[get_listar_areas_service] = lambda: ListarAreasService(repo_area)
    app.dependency_overrides[get_obtener_area_service] = lambda: ObtenerAreaService(repo_area)
    app.dependency_overrides[get_actualizar_area_service] = lambda: ActualizarAreaService(repo_area)
    app.dependency_overrides[get_eliminar_area_service] = (
        lambda: EliminarAreaService(repo_area, verificador_uso)
    )

    app.dependency_overrides[get_crear_categoria_service] = (
        lambda: CrearCategoriaService(repo_categoria)
    )
    app.dependency_overrides[get_listar_categorias_service] = (
        lambda: ListarCategoriasService(repo_categoria)
    )
    app.dependency_overrides[get_obtener_categoria_service] = (
        lambda: ObtenerCategoriaService(repo_categoria)
    )
    app.dependency_overrides[get_actualizar_categoria_service] = (
        lambda: ActualizarCategoriaService(repo_categoria)
    )
    app.dependency_overrides[get_eliminar_categoria_service] = (
        lambda: EliminarCategoriaService(repo_categoria, verificador_uso)
    )

    app.dependency_overrides[get_crear_condicion_service] = (
        lambda: CrearCondicionService(repo_condicion)
    )
    app.dependency_overrides[get_listar_condiciones_service] = (
        lambda: ListarCondicionesService(repo_condicion)
    )
    app.dependency_overrides[get_obtener_condicion_service] = (
        lambda: ObtenerCondicionService(repo_condicion)
    )
    app.dependency_overrides[get_actualizar_condicion_service] = (
        lambda: ActualizarCondicionService(repo_condicion)
    )
    app.dependency_overrides[get_eliminar_condicion_service] = (
        lambda: EliminarCondicionService(repo_condicion, verificador_uso)
    )

    app.dependency_overrides[get_crear_sede_service] = lambda: CrearSedeService(repo_sede)
    app.dependency_overrides[get_listar_sedes_service] = lambda: ListarSedesService(repo_sede)
    app.dependency_overrides[get_obtener_sede_service] = lambda: ObtenerSedeService(repo_sede)
    app.dependency_overrides[get_actualizar_sede_service] = (
        lambda: ActualizarSedeService(repo_sede)
    )
    app.dependency_overrides[get_eliminar_sede_service] = (
        lambda: EliminarSedeService(repo_sede, repo_lugar)
    )

    app.dependency_overrides[get_crear_lugar_service] = (
        lambda: CrearLugarService(repo_lugar, repo_sede)
    )
    app.dependency_overrides[get_listar_lugares_service] = (
        lambda: ListarLugaresService(repo_lugar)
    )
    app.dependency_overrides[get_obtener_lugar_service] = lambda: ObtenerLugarService(repo_lugar)
    app.dependency_overrides[get_actualizar_lugar_service] = (
        lambda: ActualizarLugarService(repo_lugar)
    )
    app.dependency_overrides[get_eliminar_lugar_service] = (
        lambda: EliminarLugarService(repo_lugar, verificador_uso)
    )

    identidad_admin = IdentidadUsuarioAutenticada(
        id_usuario="0", email="admin@example.com", nombre="Admin", rol="administrador_general"
    )
    app.dependency_overrides[requiere_usuario_autenticado] = lambda: identidad_admin

    return TestClient(app)


def test_crear_listar_obtener_actualizar_y_eliminar_area_de_punta_a_punta():
    cliente = _crear_cliente_de_prueba()

    respuesta_crear = cliente.post("/api/areas", json={"nombre": "Direccion"})
    assert respuesta_crear.status_code == 201
    id_area = respuesta_crear.json()["data"]["id"]

    assert cliente.get("/api/areas").json()["data"] == [
        {"id": id_area, "nombre": "Direccion", "descripcion": None}
    ]

    respuesta_actualizar = cliente.put(
        f"/api/areas/{id_area}", json={"nombre": "Direccion General"}
    )
    assert respuesta_actualizar.status_code == 200
    assert respuesta_actualizar.json()["data"]["nombre"] == "Direccion General"

    respuesta_eliminar = cliente.delete(f"/api/areas/{id_area}")
    assert respuesta_eliminar.status_code == 200
    assert cliente.get(f"/api/areas/{id_area}").status_code == 404


def test_crear_area_con_nombre_duplicado_retorna_409_con_code_cat_001():
    cliente = _crear_cliente_de_prueba()
    cliente.post("/api/areas", json={"nombre": "Direccion"})

    respuesta = cliente.post("/api/areas", json={"nombre": "Direccion"})

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "CAT-001"


def test_crear_listar_y_eliminar_categoria_de_punta_a_punta():
    cliente = _crear_cliente_de_prueba()

    respuesta_crear = cliente.post("/api/categorias", json={"nombre": "Muebles"})
    assert respuesta_crear.status_code == 201
    id_categoria = respuesta_crear.json()["data"]["id"]

    assert len(cliente.get("/api/categorias").json()["data"]) == 1

    respuesta_eliminar = cliente.delete(f"/api/categorias/{id_categoria}")
    assert respuesta_eliminar.status_code == 200
    assert cliente.get(f"/api/categorias/{id_categoria}").status_code == 404


def test_crear_condicion_con_color_invalido_retorna_422():
    cliente = _crear_cliente_de_prueba()

    respuesta = cliente.post("/api/condiciones", json={"nombre": "Bueno", "color": "rojo"})

    assert respuesta.status_code == 422


def test_crear_y_obtener_condicion_de_punta_a_punta():
    cliente = _crear_cliente_de_prueba()

    respuesta_crear = cliente.post(
        "/api/condiciones", json={"nombre": "Bueno", "color": "#4CAF50"}
    )
    assert respuesta_crear.status_code == 201
    id_condicion = respuesta_crear.json()["data"]["id"]

    respuesta_obtener = cliente.get(f"/api/condiciones/{id_condicion}")
    assert respuesta_obtener.status_code == 200
    assert respuesta_obtener.json()["data"]["color"] == "#4CAF50"


def test_crear_listar_actualizar_y_eliminar_sede_de_punta_a_punta():
    cliente = _crear_cliente_de_prueba()

    respuesta_crear = cliente.post("/api/sedes", json={"nombre": "Prado"})
    assert respuesta_crear.status_code == 201
    id_sede = respuesta_crear.json()["data"]["id"]

    assert len(cliente.get("/api/sedes").json()["data"]) == 1

    respuesta_actualizar = cliente.put(f"/api/sedes/{id_sede}", json={"nombre": "Prado Norte"})
    assert respuesta_actualizar.status_code == 200
    assert respuesta_actualizar.json()["data"]["nombre"] == "Prado Norte"

    respuesta_eliminar = cliente.delete(f"/api/sedes/{id_sede}")
    assert respuesta_eliminar.status_code == 200
    assert cliente.get(f"/api/sedes/{id_sede}").status_code == 404


def test_crear_lugar_requiere_una_sede_existente():
    cliente = _crear_cliente_de_prueba()

    respuesta = cliente.post(
        "/api/lugares", json={"nombre": "Bodega", "tipo": "bodega", "sede_id": "inexistente"}
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "CAT-009"


def test_crear_y_listar_lugares_filtrando_por_sede():
    cliente = _crear_cliente_de_prueba()
    id_prado = cliente.post("/api/sedes", json={"nombre": "Prado"}).json()["data"]["id"]
    id_bosa = cliente.post("/api/sedes", json={"nombre": "Bosa"}).json()["data"]["id"]

    cliente.post(
        "/api/lugares", json={"nombre": "Bodega", "tipo": "bodega", "sede_id": id_prado}
    )
    cliente.post(
        "/api/lugares", json={"nombre": "Bodega", "tipo": "bodega", "sede_id": id_bosa}
    )

    respuesta = cliente.get("/api/lugares", params={"sede_id": id_prado})

    assert respuesta.status_code == 200
    assert len(respuesta.json()["data"]) == 1
    assert respuesta.json()["data"][0]["sede_id"] == id_prado


def test_eliminar_sede_con_lugares_retorna_409_con_code_cat_010():
    cliente = _crear_cliente_de_prueba()
    id_sede = cliente.post("/api/sedes", json={"nombre": "Prado"}).json()["data"]["id"]
    cliente.post("/api/lugares", json={"nombre": "Bodega", "tipo": "bodega", "sede_id": id_sede})

    respuesta = cliente.delete(f"/api/sedes/{id_sede}")

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "CAT-010"
