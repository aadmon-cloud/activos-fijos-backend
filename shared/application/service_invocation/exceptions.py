class ErrorInvocacionServicioExterno(Exception):
    def __init__(self, nombre_servicio: str, detalle: str, status_code: int | None = None):
        super().__init__(f"Error invocando '{nombre_servicio}': {detalle}")
        self.nombre_servicio = nombre_servicio
        self.detalle = detalle
        self.status_code = status_code


class ErrorAutenticacionServicioExterno(Exception):
    def __init__(self, nombre_servicio: str, detalle: str):
        super().__init__(f"Error de autenticacion invocando '{nombre_servicio}': {detalle}")
        self.nombre_servicio = nombre_servicio
        self.detalle = detalle


class ErrorServicioExternoNoConfigurado(Exception):
    def __init__(self, nombre_servicio: str):
        super().__init__(f"El servicio '{nombre_servicio}' no esta configurado.")
        self.nombre_servicio = nombre_servicio
