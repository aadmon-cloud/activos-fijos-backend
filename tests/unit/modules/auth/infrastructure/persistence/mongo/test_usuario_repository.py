from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

from modules.auth.domain.entities.usuario import Usuario
from modules.auth.infrastructure.persistence.mongo.usuario_repository import (
    MongoUsuarioRepository,
)
from shared.domain.entities.audit_persona import AuditPersona


def _db_falsa():
    coleccion = MagicMock()
    coleccion.insert_one = AsyncMock()
    db = MagicMock()
    db.__getitem__ = MagicMock(return_value=coleccion)
    return db, coleccion


async def test_crear_autoregistro_completa_creado_por_con_el_propio_id():
    db, coleccion = _db_falsa()
    repo = MongoUsuarioRepository(db)
    usuario = Usuario.crear(email="a@b.com", username="a", password_hash="hash")
    assert usuario.creado_por.id_persona == ""  # placeholder, ver Usuario.crear()

    usuario_creado = await repo.crear(usuario)

    assert usuario_creado.creado_por.id_persona == usuario_creado.id
    doc_insertado = coleccion.insert_one.call_args.args[0]
    assert doc_insertado["creado_por"]["id_persona"] == doc_insertado["_id"]


async def test_crear_por_admin_no_pisa_el_id_persona_real():
    db, coleccion = _db_falsa()
    repo = MongoUsuarioRepository(db)
    admin_id = "507f1f77bcf86cd799439099"
    usuario = Usuario.crear_por_admin(
        email="nuevo@b.com",
        username="nuevo",
        password_hash=None,
        rol="operativo",
        creado_por=AuditPersona(id_persona=admin_id, nombre="admin", fecha=datetime.now(UTC)),
    )

    usuario_creado = await repo.crear(usuario)

    # El creador sigue siendo el admin, no el usuario recien creado.
    assert usuario_creado.creado_por.id_persona == admin_id
    assert usuario_creado.creado_por.id_persona != usuario_creado.id
    doc_insertado = coleccion.insert_one.call_args.args[0]
    assert str(doc_insertado["creado_por"]["id_persona"]) == admin_id
