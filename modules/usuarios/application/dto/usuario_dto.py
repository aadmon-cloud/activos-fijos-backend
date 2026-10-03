from dataclasses import dataclass

from modules.usuarios.domain.entities import Usuario


@dataclass
class UsuarioDTO:
    id: str
    email: str
    nombre: str
    apellido: str
    rol: str
    area_id: str | None
    telefono: str | None
    identificacion: str | None
    activo: bool


def usuario_a_dto(usuario: Usuario) -> UsuarioDTO:
    return UsuarioDTO(
        id=usuario.id,
        email=usuario.email,
        nombre=usuario.nombre,
        apellido=usuario.apellido,
        rol=usuario.rol.value,
        area_id=usuario.area_id,
        telefono=usuario.telefono,
        identificacion=usuario.identificacion,
        activo=usuario.activo,
    )
