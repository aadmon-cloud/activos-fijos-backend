class TokenUsuarioInvalidoError(Exception):
    def __init__(self, detalle: str):
        super().__init__(f"Token invalido: {detalle}")
        self.detalle = detalle
