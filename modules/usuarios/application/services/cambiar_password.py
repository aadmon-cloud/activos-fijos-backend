from dataclasses import replace
from datetime import UTC, datetime

from modules.usuarios.application.dto.cambiar_password_dto import CambiarPasswordDTO
from modules.usuarios.application.ports.hasher import HasherPort
from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.domain.errors import (
    PasswordActualIncorrectaError,
    PasswordDebilError,
    PasswordNuevaIgualALaActualError,
    UsuarioNoEncontradoError,
)
from modules.usuarios.domain.reglas import LONGITUD_MINIMA_PASSWORD
from shared.domain.entities.audit import AuditPersona


class CambiarPasswordService:
    def __init__(self, usuario_repository: UsuarioRepositoryPort, hasher: HasherPort):
        self._usuario_repository = usuario_repository
        self._hasher = hasher

    async def ejecutar(self, dto: CambiarPasswordDTO) -> None:
        usuario = await self._usuario_repository.obtener_por_id(dto.id_usuario)
        if usuario is None:
            raise UsuarioNoEncontradoError(dto.id_usuario)

        if not self._hasher.verificar(dto.password_actual, usuario.password_hash):
            raise PasswordActualIncorrectaError()

        if len(dto.password_nueva) < LONGITUD_MINIMA_PASSWORD:
            raise PasswordDebilError()

        if dto.password_nueva == dto.password_actual:
            raise PasswordNuevaIgualALaActualError()

        usuario_actualizado = replace(
            usuario,
            password_hash=self._hasher.hashear(dto.password_nueva),
            actualizado_por=AuditPersona(
                id_persona=usuario.id,
                nombre=f"{usuario.nombre} {usuario.apellido}",
                fecha=datetime.now(UTC),
            ),
        )
        await self._usuario_repository.guardar(usuario_actualizado)
