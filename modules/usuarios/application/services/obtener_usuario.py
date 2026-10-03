from modules.usuarios.application.dto.usuario_dto import UsuarioDTO, usuario_a_dto
from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.domain.errors import UsuarioNoEncontradoError


class ObtenerUsuarioService:
    def __init__(self, usuario_repository: UsuarioRepositoryPort):
        self._usuario_repository = usuario_repository

    async def ejecutar(self, id_usuario: str) -> UsuarioDTO:
        usuario = await self._usuario_repository.obtener_por_id(id_usuario)
        if usuario is None:
            raise UsuarioNoEncontradoError(id_usuario)
        return usuario_a_dto(usuario)
