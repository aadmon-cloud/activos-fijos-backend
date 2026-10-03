import bcrypt

from modules.usuarios.application.ports.hasher import HasherPort


class BcryptHasher(HasherPort):
    def hashear(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def verificar(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
