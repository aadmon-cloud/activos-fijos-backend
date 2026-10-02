from pydantic import BaseModel, Field, field_validator

TIPOS_ORIGEN_VALIDOS = {"compra", "donacion", "devolucion", "traslado", "ajuste"}


class ItemEntradaMultipleInput(BaseModel):
    producto_codigo: str = Field(min_length=1)
    cantidad: int = Field(gt=0)
    ubicacion: str | None = None


class RegistrarEntradaMultipleInput(BaseModel):
    productos: list[ItemEntradaMultipleInput] = Field(min_length=1)
    tipo_origen: str
    origen_nombre: str = Field(min_length=1)
    ubicacion: str | None = None
    notas: str | None = None

    @field_validator("tipo_origen")
    @classmethod
    def _validar_tipo_origen(cls, v: str) -> str:
        v_normalizado = v.lower()
        if v_normalizado not in TIPOS_ORIGEN_VALIDOS:
            raise ValueError(
                f"tipo_origen debe ser uno de: {', '.join(sorted(TIPOS_ORIGEN_VALIDOS))}"
            )
        return v_normalizado
