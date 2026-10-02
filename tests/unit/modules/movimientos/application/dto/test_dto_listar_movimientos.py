import pytest
from pydantic import ValidationError

from modules.movimientos.application.dto.listar_movimientos import ListarMovimientosInput


@pytest.mark.parametrize(
    "tipo", ["entrada", "salida", "creacion_ubicacion", "transferencia_ubicacion"]
)
def test_acepta_los_4_tipos_de_movimiento(tipo):
    entrada = ListarMovimientosInput(tipo=tipo)

    assert entrada.tipo == tipo


def test_rechaza_un_tipo_desconocido():
    with pytest.raises(ValidationError):
        ListarMovimientosInput(tipo="no-existe")
