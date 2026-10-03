"""Migra usuarios del backend legacy hacia el modulo `usuarios`.

Debe ejecutarse DESPUES de `scripts/migrar_catalogos.py` (ver docs/plan_migracion_activos_fijos.md,
seccion 8.3): resuelve `area_id` buscando el area legacy por su `_id` y encontrando el area ya
migrada con el mismo nombre. Si el area legacy referenciada no existe o no fue migrada, el usuario
se migra con `area_id=None` en vez de fallar.

Preserva el hash de password legacy (bcrypt via passlib, compatible con `bcrypt.checkpw`) en vez
de pedir una password en texto plano -- por eso construye la entidad `Usuario` directamente y usa
el repositorio, sin pasar por `RegistrarUsuarioService` (que espera una password sin hashear).

Mapeo de rol: `admin`/`super_admin` -> `administrador_general`; cualquier otro rol (incluye
`empleado`) -> `empleado`. Es idempotente: si el email ya existe, se omite.

Uso:
    python -m scripts.migrar_usuarios

Variables de entorno adicionales (ademas de las que ya usa la app nueva, ej. MONGO_URL/MONGO_DB):
    LEGACY_MONGO_URL   default: mongodb://localhost:27017
    LEGACY_MONGO_DB    default: GESTIONACTIVOSFIJOS
"""

import asyncio
from datetime import UTC, datetime

from bson import ObjectId

from config.logger import configurar_logging
from modules.catalogos.infrastructure.persistence.mongo.area_repository import (
    MongoAreaRepository,
)
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.infrastructure.persistence.mongo.usuario_repository import (
    MongoUsuarioRepository,
)
from scripts._legacy_db import conectar_legacy
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

_CREADO_POR_ID = "migracion-legacy"
_CREADO_POR_NOMBRE = "Migracion de datos legacy"
_ROLES_LEGACY_ADMINISTRADOR_GENERAL = {"admin", "super_admin"}


def _mapear_rol(rol_legacy: str) -> RolUsuario:
    if rol_legacy in _ROLES_LEGACY_ADMINISTRADOR_GENERAL:
        return RolUsuario.ADMINISTRADOR_GENERAL
    return RolUsuario.EMPLEADO


async def _resolver_area_id_nueva(
    area_repository: MongoAreaRepository, db_legacy, area_id_legacy: str | None
) -> str | None:
    if not area_id_legacy:
        return None

    area_legacy = db_legacy["areas"].find_one({"_id": ObjectId(area_id_legacy)})
    if area_legacy is None:
        return None

    area_nueva = await area_repository.obtener_por_nombre(area_legacy["nombre"])
    return area_nueva.id if area_nueva else None


async def _migrar_usuarios(db_legacy) -> None:
    usuario_repository = MongoUsuarioRepository()
    area_repository = MongoAreaRepository()

    for doc in db_legacy["usuarios"].find({}):
        email = doc["email"].strip().lower()

        if await usuario_repository.obtener_por_email(email) is not None:
            print(f"  usuario ya existia, se omite: {email}")
            continue

        area_id_nueva = await _resolver_area_id_nueva(
            area_repository, db_legacy, doc.get("area_id")
        )
        rol_legacy = doc.get("rol", "empleado")
        rol_nuevo = _mapear_rol(rol_legacy)

        usuario = Usuario(
            id=None,
            email=email,
            nombre=doc["nombre"],
            apellido=doc["apellido"],
            password_hash=doc["password"],
            rol=rol_nuevo,
            area_id=area_id_nueva,
            telefono=doc.get("telefono"),
            identificacion=doc.get("identificacion"),
            activo=doc.get("activo", True),
            creado_por=AuditPersona(
                id_persona=_CREADO_POR_ID,
                nombre=_CREADO_POR_NOMBRE,
                fecha=datetime.now(UTC),
            ),
            actualizado_por=None,
        )

        await usuario_repository.guardar(usuario)
        print(f"  usuario migrado: {email} (rol legacy='{rol_legacy}' -> '{rol_nuevo.value}')")


async def _ejecutar() -> None:
    cliente_legacy, db_legacy = conectar_legacy()
    mongo_manager.connect()
    try:
        print("Migrando usuarios...")
        await _migrar_usuarios(db_legacy)
    finally:
        mongo_manager.close()
        cliente_legacy.close()


if __name__ == "__main__":
    configurar_logging()
    asyncio.run(_ejecutar())
