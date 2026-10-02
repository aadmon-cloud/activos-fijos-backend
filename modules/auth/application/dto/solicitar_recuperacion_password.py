from pydantic import BaseModel, Field


class SolicitarRecuperacionPasswordInput(BaseModel):
    email: str = Field(min_length=1)
