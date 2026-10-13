from modules.activos.application.ports.almacen_fotos import AlmacenFotosPort, FotoAlmacenada
from modules.activos.domain.errors import FotoNoEncontradaError


class ObtenerFotoActivoService:
    def __init__(self, almacen_fotos: AlmacenFotosPort):
        self._almacen_fotos = almacen_fotos

    async def ejecutar(self, id_activo: str) -> FotoAlmacenada:
        foto = await self._almacen_fotos.obtener(id_activo)
        if foto is None:
            raise FotoNoEncontradaError(id_activo)

        return foto
