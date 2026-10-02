from pydantic import BaseModel, Field


class TransferirStockInput(BaseModel):
    origen: str = Field(min_length=1, max_length=100)
    destino: str = Field(min_length=1, max_length=100)
    cantidad: int = Field(ge=1)
