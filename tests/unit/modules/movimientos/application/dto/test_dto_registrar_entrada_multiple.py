import pytest
from pydantic import ValidationError

from modules.movimientos.application.dto.registrar_entrada_multiple import (
    ItemEntradaMultipleInput,
    RegistrarEntradaMultipleInput,
)


def _item():
    return ItemEntradaMultipleInput(producto_codigo="PROD-001", cantidad=1)


def test_normaliza_tipo_origen_a_minusculas():
    entrada = RegistrarEntradaMultipleInput(
        productos=[_item()], tipo_origen="COMPRA", origen_nombre="Proveedor X"
    )

    assert entrada.tipo_origen == "compra"


def test_tipo_origen_invalido_lanza_error_de_validacion():
    with pytest.raises(ValidationError):
        RegistrarEntradaMultipleInput(
            productos=[_item()], tipo_origen="no-es-valido", origen_nombre="Proveedor X"
        )


def test_productos_vacio_lanza_error_de_validacion():
    with pytest.raises(ValidationError):
        RegistrarEntradaMultipleInput(
            productos=[], tipo_origen="compra", origen_nombre="Proveedor X"
        )
