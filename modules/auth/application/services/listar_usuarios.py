from shared.application.dto.pagination import RespuestaPaginada

from modules.auth.application.dto.listar_usuarios import ListarUsuariosInput
from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.domain.entities.usuario import Usuario


class ListarUsuariosService:
    def __init__(self, usuario_repository: UsuarioRepositoryPort):
        self._usuario_repository = usuario_repository

    async def ejecutar(self, entrada: ListarUsuariosInput) -> RespuestaPaginada[Usuario]:
        usuarios, total = await self._usuario_repository.listar_paginado(
            pagina=entrada.pagina, limite=entrada.limite
        )
        return RespuestaPaginada.crear(
            items=usuarios, page=entrada.pagina, limit=entrada.limite, total=total
        )
