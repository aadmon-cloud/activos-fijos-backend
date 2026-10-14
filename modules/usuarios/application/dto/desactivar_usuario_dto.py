from dataclasses import dataclass


@dataclass
class DesactivarUsuarioDTO:
    id_usuario: str
    actualizado_por_id: str
    actualizado_por_nombre: str

    # Rol de quien ejecuta la accion; vacio = sin privilegios.
    actor_rol: str = ""
