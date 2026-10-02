from pydantic import BaseModel, Field

from modules.reservas.application.dto.ajuste_item import AjusteItemInput


class AjustarReservaInput(BaseModel):
    ajustes: list[AjusteItemInput] = Field(min_length=1)
    datos_adicionales: dict | None = None
