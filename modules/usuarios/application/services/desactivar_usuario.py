from dataclasses import replace
from datetime import UTC, datetime

from modules.usuarios.application.dto.desactivar_usuario_dto import DesactivarUsuarioDTO
from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.domain.errors import (
    GestionSuperAdministradorNoPermitidaError,
    UsuarioNoEncontradoError,
)
from modules.usuarios.domain.reglas import puede_gestionar_rol
from shared.domain.entities.audit import AuditPersona


class DesactivarUsuarioService:
    def __init__(self, usuario_repository: UsuarioRepositoryPort):
        self._usuario_repository = usuario_repository

    async def ejecutar(self, dto: DesactivarUsuarioDTO) -> None:
        usuario = await self._usuario_repository.obtener_por_id(dto.id_usuario)
        if usuario is None:
            raise UsuarioNoEncontradoError(dto.id_usuario)

        if not puede_gestionar_rol(dto.actor_rol, usuario.rol):
            raise GestionSuperAdministradorNoPermitidaError()

        if not usuario.activo:
            return

        usuario_desactivado = replace(
            usuario,
            activo=False,
            actualizado_por=AuditPersona(
                id_persona=dto.actualizado_por_id,
                nombre=dto.actualizado_por_nombre,
                fecha=datetime.now(UTC),
            ),
        )
        await self._usuario_repository.guardar(usuario_desactivado)
