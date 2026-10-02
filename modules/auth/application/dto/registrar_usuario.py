from pydantic import BaseModel, Field


class RegistrarUsuarioInput(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)
    username: str | None = Field(default=None, min_length=3, max_length=50)
