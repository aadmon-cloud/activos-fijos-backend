from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from modules.auth.application.ports.usuario_repository import UsuarioRepositoryPort
from modules.auth.domain.entities.usuario import Usuario
from modules.auth.infrastructure.persistence.mongo.pipelines.usuario_pipeline import (
    UsuarioPipelineBuilder,
)

COLECCION = "usuarios"


class MongoUsuarioRepository(UsuarioRepositoryPort):
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db[COLECCION]

    async def obtener_por_email(self, email: str) -> Usuario | None:
        doc = await self._col.find_one({"email": email})
        return self._doc_a_usuario(doc) if doc else None

    async def obtener_por_id(self, usuario_id: str) -> Usuario | None:
        if not ObjectId.is_valid(usuario_id):
            return None
        doc = await self._col.find_one({"_id": ObjectId(usuario_id)})
        return self._doc_a_usuario(doc) if doc else None

    async def existe_por_email(self, email: str) -> bool:
        return await self._col.count_documents({"email": email}, limit=1) > 0

    async def existe_por_username(self, username: str) -> bool:
        return await self._col.count_documents({"username": username}, limit=1) > 0

    async def obtener_por_token_reset(self, token: str) -> Usuario | None:
        doc = await self._col.find_one({"reset_password_token": token})
        return self._doc_a_usuario(doc) if doc else None

    async def obtener_por_google_id(self, google_id: str) -> Usuario | None:
        doc = await self._col.find_one({"google_id": google_id})
        return self._doc_a_usuario(doc) if doc else None

    async def crear(self, usuario: Usuario) -> Usuario:
        # El _id de Mongo no existe hasta insertar. En auto-registro/Google,
        # `creado_por.id_persona` llega vacío porque el creador es el propio
        # usuario nuevo — se completa acá con el id recién generado. Si ya
        # viene con un id_persona real (creación por un admin distinto, ver
        # incremento 4), NO se pisa.
        nuevo_id = ObjectId()
        creado_por = usuario.creado_por
        if not creado_por.id_persona:
            creado_por = creado_por.model_copy(update={"id_persona": str(nuevo_id)})

        usuario_con_id = usuario.model_copy(
            update={"id": str(nuevo_id), "creado_por": creado_por}
        )
        doc = self._entidad_a_doc(usuario_con_id)
        doc["_id"] = nuevo_id
        await self._col.insert_one(doc)
        return usuario_con_id

    async def actualizar(self, usuario: Usuario) -> Usuario:
        doc = self._entidad_a_doc(usuario)
        await self._col.replace_one({"_id": ObjectId(usuario.id)}, doc)
        return usuario

    async def listar_paginado(self, pagina: int, limite: int) -> tuple[list[Usuario], int]:
        pipeline = (
            UsuarioPipelineBuilder()
            .ordenar_por_fecha_creacion_desc()
            .paginar(pagina, limite)
            .construir()
        )
        cursor = self._col.aggregate(pipeline)
        resultados = await cursor.to_list(length=1)

        if not resultados:
            return [], 0

        resultado = resultados[0]
        usuarios = [self._doc_a_usuario(doc) for doc in resultado.get("resultado", [])]
        return usuarios, resultado.get("total_elementos", 0)

    async def eliminar(self, usuario_id: str) -> bool:
        if not ObjectId.is_valid(usuario_id):
            return False
        resultado = await self._col.delete_one({"_id": ObjectId(usuario_id)})
        return resultado.deleted_count > 0

    def _entidad_a_doc(self, usuario: Usuario) -> dict:
        doc = usuario.model_dump(exclude={"id"})
        doc["rol"] = usuario.rol.value
        doc["creado_por"]["id_persona"] = ObjectId(usuario.creado_por.id_persona)
        if usuario.actualizado_por:
            doc["actualizado_por"]["id_persona"] = ObjectId(
                usuario.actualizado_por.id_persona
            )
        return doc

    def _doc_a_usuario(self, doc: dict) -> Usuario:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        doc["creado_por"]["id_persona"] = str(doc["creado_por"]["id_persona"])
        if doc.get("actualizado_por"):
            doc["actualizado_por"]["id_persona"] = str(
                doc["actualizado_por"]["id_persona"]
            )
        return Usuario(**doc)
