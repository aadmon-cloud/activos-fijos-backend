class TokenInvalidoError(Exception):
    def __init__(self, detalle: str):
        super().__init__(f"Token invalido: {detalle}")
        self.detalle = detalle


class EmailTokenNoDisponibleError(Exception):
    def __init__(self):
        super().__init__("El token no incluye un email valido.")
