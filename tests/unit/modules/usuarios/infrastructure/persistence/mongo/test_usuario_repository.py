from datetime import UTC, datetime

from bson import ObjectId

from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.infrastructure.persistence.mongo.usuario_repository import (
    _doc_a_entidad,
    _entidad_a_doc,
)
from shared.domain.entities.audit import AuditPersona


def _usuario(**overrides) -> Usuario:
    valores = dict(
        id=None,
        email="ana@example.com",
        nombre="Ana",
        apellido="Garcia",
        password_hash="hash",
        rol=RolUsuario.EMPLEADO,
        area_id=None,
        telefono=None,
        identificacion=None,
        activo=True,
        creado_por=AuditPersona(
            id_persona="0", nombre="Sistema", fecha=datetime(2026, 1, 1, tzinfo=UTC)
        ),
        actualizado_por=None,
    )
    valores.update(overrides)
    return Usuario(**valores)


def test_entidad_a_doc_no_incluye_el_id():
    doc = _entidad_a_doc(_usuario())

    assert "id" not in doc
    assert "_id" not in doc
    assert doc["email"] == "ana@example.com"
    assert doc["rol"] == "empleado"


def test_entidad_a_doc_convierte_area_id_a_object_id():
    area_id = str(ObjectId())

    doc = _entidad_a_doc(_usuario(area_id=area_id))

    assert doc["area_id"] == ObjectId(area_id)


def test_entidad_a_doc_deja_area_id_en_none_si_no_hay_area():
    doc = _entidad_a_doc(_usuario(area_id=None))

    assert doc["area_id"] is None


def test_doc_a_entidad_convierte_object_id_a_string_y_rol_a_enum():
    object_id = ObjectId()
    area_id = ObjectId()
    doc = {
        "_id": object_id,
        "email": "ana@example.com",
        "nombre": "Ana",
        "apellido": "Garcia",
        "password_hash": "hash",
        "rol": "jefe_area",
        "area_id": area_id,
        "telefono": None,
        "identificacion": None,
        "activo": True,
        "creado_por": {
            "id_persona": "0",
            "nombre": "Sistema",
            "fecha": datetime(2026, 1, 1, tzinfo=UTC),
        },
        "actualizado_por": None,
    }

    usuario = _doc_a_entidad(doc)

    assert usuario.id == str(object_id)
    assert usuario.rol == RolUsuario.JEFE_AREA
    assert usuario.area_id == str(area_id)
    assert usuario.creado_por.nombre == "Sistema"
    assert usuario.actualizado_por is None
