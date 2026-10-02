import bcrypt

from modules.auth.application.ports.password_hasher import PasswordHasherPort


class BcryptPasswordHasher(PasswordHasherPort):
    def hashear(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verificar(self, password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
