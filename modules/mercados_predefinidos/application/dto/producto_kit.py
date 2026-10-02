from pydantic import BaseModel, Field


class ProductoKitInput(BaseModel):
    producto_id: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
