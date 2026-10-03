from dataclasses import replace
from datetime import UTC, datetime

from modules.usuarios.application.dto.actualizar_usuario_dto import ActualizarUsuarioDTO
from modules.usuarios.application.dto.usuario_dto import UsuarioDTO, usuario_a_dto
from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.application.ports.verificador_area import VerificadorAreaPort
from modules.usuarios.domain.errors import AreaInvalidaError, UsuarioNoEncontradoError
from shared.domain.entities.audit import AuditPersona


class ActualizarUsuarioService:
    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        verificador_area: VerificadorAreaPort,
    ):
        self._usuario_repository = usuario_repository
        self._verificador_area = verificador_area

    async def ejecutar(self, dto: ActualizarUsuarioDTO) -> UsuarioDTO:
        usuario = await self._usuario_repository.obtener_por_id(dto.id_usuario)
        if usuario is None:
            raise UsuarioNoEncontradoError(dto.id_usuario)

        if dto.area_id is not None and not await self._verificador_area.existe(dto.area_id):
            raise AreaInvalidaError(dto.area_id)

        usuario_actualizado = replace(
            usuario,
            nombre=dto.nombre if dto.nombre is not None else usuario.nombre,
            apellido=dto.apellido if dto.apellido is not None else usuario.apellido,
            rol=dto.rol if dto.rol is not None else usuario.rol,
            area_id=dto.area_id if dto.area_id is not None else usuario.area_id,
            telefono=dto.telefono if dto.telefono is not None else usuario.telefono,
            actualizado_por=AuditPersona(
                id_persona=dto.actualizado_por_id,
                nombre=dto.actualizado_por_nombre,
                fecha=datetime.now(UTC),
            ),
        )

        usuario_guardado = await self._usuario_repository.guardar(usuario_actualizado)
        return usuario_a_dto(usuario_guardado)
