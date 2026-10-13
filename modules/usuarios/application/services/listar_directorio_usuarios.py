from dataclasses import dataclass

from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort

_LIMITE_MAXIMO = 1000


@dataclass(frozen=True)
class UsuarioDirectorioDTO:
    """Lo minimo para elegir a una persona (p. ej. a quien se le presta un activo): sin correo, rol ni datos de
    contacto, que solo ve el administrador."""

    id: str
    nombre: str
    apellido: str


class ListarDirectorioUsuariosService:
    """Directorio de personas activas, visible para cualquier usuario autenticado."""

    def __init__(self, usuario_repository: UsuarioRepositoryPort):
        self._usuario_repository = usuario_repository

    async def ejecutar(self, busqueda: str | None = None, limit: int = _LIMITE_MAXIMO) -> list[UsuarioDirectorioDTO]:
        usuarios = await self._usuario_repository.listar(
            busqueda=busqueda, skip=0, limit=min(limit, _LIMITE_MAXIMO)
        )

        return [
            UsuarioDirectorioDTO(id=usuario.id, nombre=usuario.nombre, apellido=usuario.apellido)
            for usuario in usuarios
            if usuario.activo
        ]
