import secrets
from datetime import UTC, datetime

from modules.usuarios.application.dto.registrar_usuario_dto import RegistrarUsuarioDTO
from modules.usuarios.application.dto.usuario_dto import UsuarioDTO, usuario_a_dto
from modules.usuarios.application.ports.hasher import HasherPort
from modules.usuarios.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.usuarios.application.ports.verificador_area import VerificadorAreaPort
from modules.usuarios.domain.entities import Usuario
from modules.usuarios.domain.errors import (
    AreaInvalidaError,
    EmailYaRegistradoError,
    GestionSuperAdministradorNoPermitidaError,
    IdentificacionYaRegistradaError,
    PasswordDebilError,
)
from modules.usuarios.domain.reglas import LONGITUD_MINIMA_PASSWORD, puede_gestionar_rol
from shared.domain.entities.audit import AuditPersona


class RegistrarUsuarioService:
    def __init__(
        self,
        usuario_repository: UsuarioRepositoryPort,
        hasher: HasherPort,
        verificador_area: VerificadorAreaPort,
    ):
        self._usuario_repository = usuario_repository
        self._hasher = hasher
        self._verificador_area = verificador_area

    async def ejecutar(self, dto: RegistrarUsuarioDTO) -> UsuarioDTO:
        if not puede_gestionar_rol(dto.actor_rol, dto.rol):
            raise GestionSuperAdministradorNoPermitidaError()

        email = dto.email.strip().lower()

        if dto.password is not None and len(dto.password) < LONGITUD_MINIMA_PASSWORD:
            raise PasswordDebilError()

        if await self._usuario_repository.obtener_por_email(email) is not None:
            raise EmailYaRegistradoError(email)

        identificacion = dto.identificacion.strip() if dto.identificacion else None
        if identificacion is not None:
            existente = await self._usuario_repository.obtener_por_identificacion(identificacion)
            if existente is not None:
                raise IdentificacionYaRegistradaError(identificacion)

        if dto.area_id is not None and not await self._verificador_area.existe(dto.area_id):
            raise AreaInvalidaError(dto.area_id)

        usuario = Usuario(
            id=None,
            email=email,
            nombre=dto.nombre.strip(),
            apellido=dto.apellido.strip(),
            # Sin contrasena, se guarda una que nadie conoce: la cuenta solo se abre con Google.
            password_hash=self._hasher.hashear(dto.password or secrets.token_urlsafe(32)),
            rol=dto.rol,
            area_id=dto.area_id,
            telefono=dto.telefono,
            identificacion=identificacion,
            activo=True,
            creado_por=AuditPersona(
                id_persona=dto.creado_por_id,
                nombre=dto.creado_por_nombre,
                fecha=datetime.now(UTC),
            ),
            actualizado_por=None,
        )

        usuario_guardado = await self._usuario_repository.guardar(usuario)

        return usuario_a_dto(usuario_guardado)
