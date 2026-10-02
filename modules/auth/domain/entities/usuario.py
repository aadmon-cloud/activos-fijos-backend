from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from shared.domain.entities.audit_persona import AuditPersona
from shared.domain.entities.base import BaseDomainEntity


class RolUsuario(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    OPERATIVO = "operativo"


class Usuario(BaseDomainEntity):
    id: str | None = None
    email: str
    username: str
    password_hash: str | None = None
    rol: RolUsuario = RolUsuario.OPERATIVO
    activo: bool = True
    email_verificado: bool = False
    google_id: str | None = None
    google_picture: str | None = None
    reset_password_token: str | None = None
    reset_password_expires: datetime | None = None
    creado_por: AuditPersona
    actualizado_por: AuditPersona | None = None

    @classmethod
    def crear(cls, email: str, username: str, password_hash: str) -> "Usuario":
        """Usuario auto-registrado: rol siempre operativo, sin importar lo que pida el cliente.

        `creado_por.id_persona` queda vacío aquí porque el _id de Mongo aún no
        existe; el repositorio lo completa con el propio id al insertar
        (ver Fase 3 / Riesgos del módulo auth en MIGRATION_PLAN.md).
        """
        email_normalizado = email.strip().lower()
        ahora = datetime.now(UTC)

        return cls(
            id=None,
            email=email_normalizado,
            username=username,
            password_hash=password_hash,
            rol=RolUsuario.OPERATIVO,
            activo=True,
            email_verificado=False,
            creado_por=AuditPersona(id_persona="", nombre=username, fecha=ahora),
        )

    def token_reset_valido(self, token: str, ahora: datetime) -> bool:
        return (
            self.reset_password_token is not None
            and self.reset_password_token == token
            and self.reset_password_expires is not None
            and self.reset_password_expires > ahora
        )

    def generar_token_reset(
        self, token: str, expira: datetime, actualizado_por: AuditPersona
    ) -> "Usuario":
        return self.model_copy(
            update={
                "reset_password_token": token,
                "reset_password_expires": expira,
                "actualizado_por": actualizado_por,
            }
        )

    def restablecer_password(
        self, password_hash: str, actualizado_por: AuditPersona
    ) -> "Usuario":
        return self.model_copy(
            update={
                "password_hash": password_hash,
                "reset_password_token": None,
                "reset_password_expires": None,
                "actualizado_por": actualizado_por,
            }
        )

    def cambiar_password(
        self, password_hash: str, actualizado_por: AuditPersona
    ) -> "Usuario":
        return self.model_copy(
            update={"password_hash": password_hash, "actualizado_por": actualizado_por}
        )

    @classmethod
    def crear_desde_google(
        cls, email: str, username: str, google_id: str, google_picture: str | None
    ) -> "Usuario":
        """Usuario creado por primera vez vía Google: sin password, email ya
        verificado por Google, rol siempre operativo."""
        email_normalizado = email.strip().lower()
        ahora = datetime.now(UTC)

        return cls(
            id=None,
            email=email_normalizado,
            username=username,
            password_hash=None,
            rol=RolUsuario.OPERATIVO,
            activo=True,
            email_verificado=True,
            google_id=google_id,
            google_picture=google_picture,
            creado_por=AuditPersona(id_persona="", nombre=username, fecha=ahora),
        )

    def vincular_google(
        self,
        google_id: str,
        google_picture: str | None,
        actualizado_por: AuditPersona,
    ) -> "Usuario":
        """Enlaza una cuenta existente (creada por email/password) con Google,
        la primera vez que ese usuario hace login con Google."""
        return self.model_copy(
            update={
                "google_id": self.google_id or google_id,
                "google_picture": google_picture or self.google_picture,
                "email_verificado": True,
                "actualizado_por": actualizado_por,
            }
        )

    @classmethod
    def crear_por_admin(
        cls,
        email: str,
        username: str,
        password_hash: str | None,
        rol: RolUsuario,
        creado_por: AuditPersona,
    ) -> "Usuario":
        """Usuario creado por un super_admin: rol elegido explícitamente
        (a diferencia del auto-registro público), password opcional.

        `creado_por` ya viene resuelto (el admin autenticado), a diferencia de
        `crear()`/`crear_desde_google()` donde el creador es el propio usuario
        nuevo (cuyo id aún no existe al momento de construir la entidad).
        """
        return cls(
            id=None,
            email=email.strip().lower(),
            username=username,
            password_hash=password_hash,
            rol=rol,
            activo=True,
            email_verificado=False,
            creado_por=creado_por,
        )

    def actualizar_admin(
        self,
        actualizado_por: AuditPersona,
        username: str | None = None,
        rol: RolUsuario | None = None,
        activo: bool | None = None,
        password_hash: str | None = None,
    ) -> "Usuario":
        """Update parcial: solo se aplican los campos que vienen distintos de None."""
        cambios: dict = {"actualizado_por": actualizado_por}
        if username is not None:
            cambios["username"] = username
        if rol is not None:
            cambios["rol"] = rol
        if activo is not None:
            cambios["activo"] = activo
        if password_hash is not None:
            cambios["password_hash"] = password_hash
        return self.model_copy(update=cambios)
