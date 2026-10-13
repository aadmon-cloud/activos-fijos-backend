"""Crea (o repara) un administrador general que entra con su cuenta de Google.

El ingreso al sistema es solo con Google y solo para usuarios ya registrados, asi que el primer administrador no
puede crearse desde la propia aplicacion: este script lo deja registrado en la base indicada por MONGO_URL/MONGO_DB.

Es idempotente: si el correo ya existe, lo reactiva y le devuelve el rol de administrador general.

Uso:
    python -m scripts.crear_administrador --email persona@fundacionmarialuisa.org --nombre Ana --apellido Perez
"""

import argparse
import asyncio
import secrets
from dataclasses import replace
from datetime import UTC, datetime

from config.logger import configurar_logging
from modules.usuarios.domain.entities import RolUsuario, Usuario
from modules.usuarios.infrastructure.persistence.mongo.usuario_repository import (
    MongoUsuarioRepository,
)
from modules.usuarios.infrastructure.security.bcrypt_hasher import BcryptHasher
from shared.domain.entities.audit import AuditPersona
from shared.infrastructure.persistence.mongo.database import mongo_manager

_CREADO_POR_ID = "script-administrador"
_CREADO_POR_NOMBRE = "Script crear_administrador"


async def _crear_o_reparar(email: str, nombre: str, apellido: str) -> None:
    repositorio = MongoUsuarioRepository()
    email = email.strip().lower()
    audit = AuditPersona(id_persona=_CREADO_POR_ID, nombre=_CREADO_POR_NOMBRE, fecha=datetime.now(UTC))

    existente = await repositorio.obtener_por_email(email)
    if existente is not None:
        await repositorio.guardar(
            replace(existente, rol=RolUsuario.ADMINISTRADOR_GENERAL, activo=True, actualizado_por=audit)
        )
        print(f"Ya existia: {email}. Queda activo y como administrador general.")
        return

    await repositorio.guardar(
        Usuario(
            id=None,
            email=email,
            nombre=nombre.strip(),
            apellido=apellido.strip(),
            # Nadie conoce esta contrasena: la cuenta solo se abre con Google.
            password_hash=BcryptHasher().hashear(secrets.token_urlsafe(32)),
            rol=RolUsuario.ADMINISTRADOR_GENERAL,
            area_id=None,
            telefono=None,
            identificacion=None,
            activo=True,
            creado_por=audit,
            actualizado_por=None,
        )
    )
    print(f"Administrador creado: {email}")


async def _ejecutar(email: str, nombre: str, apellido: str) -> None:
    mongo_manager.connect()
    try:
        await _crear_o_reparar(email, nombre, apellido)
    finally:
        mongo_manager.close()


if __name__ == "__main__":
    configurar_logging()
    parser = argparse.ArgumentParser(description="Crea o repara un administrador general (ingreso con Google).")
    parser.add_argument("--email", required=True, help="Correo de la cuenta de Google")
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--apellido", required=True)
    argumentos = parser.parse_args()
    asyncio.run(_ejecutar(argumentos.email, argumentos.nombre, argumentos.apellido))
