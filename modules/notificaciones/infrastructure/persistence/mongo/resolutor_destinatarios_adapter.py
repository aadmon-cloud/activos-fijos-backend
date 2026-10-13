import logging

from bson import ObjectId
from bson.errors import InvalidId
from email_validator import EmailNotValidError, validate_email

from modules.notificaciones.application.ports.resolutor_destinatarios import (
    ResolutorDestinatariosPort,
)
from shared.infrastructure.persistence.mongo.database import mongo_manager

logger = logging.getLogger(__name__)

# Consulta la coleccion "usuarios" por nombre en vez de importar modules.usuarios.
_NOMBRE_COLECCION_USUARIOS = "usuarios"

PREFIJO_USUARIO = "usuario:"
PREFIJO_ROL = "rol:"
PREFIJO_AREA = "area:"


def _object_id_o_none(valor: str) -> ObjectId | None:
    try:
        return ObjectId(valor)
    except (InvalidId, TypeError):
        logger.warning("Destinatario con un id invalido: %r", valor)
        return None


def _correo_valido(texto: str) -> str | None:
    try:
        return validate_email(texto, check_deliverability=False).normalized
    except EmailNotValidError:
        logger.warning("Destinatario con un correo invalido: %r", texto)
        return None


class MongoResolutorDestinatarios(ResolutorDestinatariosPort):
    async def resolver(self, destinatarios: list[str]) -> list[str]:
        literales: list[str] = []
        condiciones: list[dict] = []

        for destinatario in destinatarios:
            if destinatario.startswith(PREFIJO_USUARIO):
                id_usuario = _object_id_o_none(destinatario.removeprefix(PREFIJO_USUARIO))
                if id_usuario:
                    condiciones.append({"_id": id_usuario})
            elif destinatario.startswith(PREFIJO_ROL):
                condiciones.append({"rol": destinatario.removeprefix(PREFIJO_ROL)})
            elif destinatario.startswith(PREFIJO_AREA):
                id_area = _object_id_o_none(destinatario.removeprefix(PREFIJO_AREA))
                if id_area:
                    condiciones.append({"area_id": id_area})
            elif correo := _correo_valido(destinatario):
                literales.append(correo)

        correos = list(literales)

        if condiciones:
            # Solo usuarios activos: un usuario desactivado ya no recibe avisos.
            documentos = (
                await mongo_manager.get_database()[_NOMBRE_COLECCION_USUARIOS]
                .find({"$or": condiciones, "activo": True}, {"email": 1})
                .to_list(length=None)
            )
            correos.extend(d["email"] for d in documentos if d.get("email"))

        # Sin repetidos (sin distinguir mayusculas) y en el orden en que aparecieron.
        vistos: dict[str, str] = {}
        for correo in correos:
            vistos.setdefault(correo.lower(), correo)

        return list(vistos.values())
