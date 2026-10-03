from modules.usuarios.application.dto.listar_usuarios_dto import ListarUsuariosDTO
from modules.usuarios.application.dto.usuario_dto import UsuarioDTO, usuario_a_dto
from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort

_LIMITE_MAXIMO = 1000


class ListarUsuariosService:
    def __init__(self, usuario_repository: UsuarioRepositoryPort):
        self._usuario_repository = usuario_repository

    async def ejecutar(self, dto: ListarUsuariosDTO) -> list[UsuarioDTO]:
        limit = min(dto.limit, _LIMITE_MAXIMO)
        usuarios = await self._usuario_repository.listar(
            busqueda=dto.busqueda, skip=dto.skip, limit=limit
        )
        return [usuario_a_dto(usuario) for usuario in usuarios]
