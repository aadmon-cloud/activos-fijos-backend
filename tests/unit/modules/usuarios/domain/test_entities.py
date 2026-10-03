import dataclasses
from datetime import UTC, datetime

import pytest

from modules.usuarios.domain.entities import RolUsuario, Usuario
from shared.domain.entities.audit import AuditPersona


def _crear_usuario(**overrides) -> Usuario:
    valores = dict(
        id="1",
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


def test_usuario_se_crea_con_los_campos_esperados():
    usuario = _crear_usuario()

    assert usuario.email == "ana@example.com"
    assert usuario.rol == RolUsuario.EMPLEADO
    assert usuario.activo is True


def test_usuario_es_inmutable():
    usuario = _crear_usuario()

    with pytest.raises(dataclasses.FrozenInstanceError):
        usuario.nombre = "Otro"


def test_rol_usuario_tiene_los_seis_roles_esperados():
    valores = {rol.value for rol in RolUsuario}

    assert valores == {
        "administrador_general",
        "tecnologia",
        "mantenimiento",
        "administrativo",
        "jefe_area",
        "empleado",
    }
