import pytest

from modules.activos.domain.fotos import (
    TAMANO_MAXIMO_FOTO_BYTES,
    detectar_tipo_imagen,
    ruta_foto,
)

JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 20
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 20


@pytest.mark.parametrize(
    "contenido, esperado",
    [(JPEG, "image/jpeg"), (PNG, "image/png"), (WEBP, "image/webp")],
)
def test_detecta_el_tipo_por_los_primeros_bytes(contenido, esperado):
    assert detectar_tipo_imagen(contenido) == esperado


@pytest.mark.parametrize(
    "contenido",
    [
        b"",
        b"GIF89a....",
        b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>",
        b"<html><script>alert(1)</script></html>",
        b"MZ\x90\x00",  # ejecutable de Windows
        b"RIFF\x24\x00\x00\x00WAVEfmt ",  # RIFF que no es WebP
        b"%PDF-1.7",
        b"\xff\xd8",  # JPEG truncado: sin el tercer byte de la firma
    ],
)
def test_rechaza_lo_que_no_es_jpeg_png_ni_webp(contenido):
    assert detectar_tipo_imagen(contenido) is None


def test_el_tipo_depende_del_contenido_no_de_lo_que_declare_el_cliente():
    # Un SVG con scripts nunca se acepta aunque se envie como "image/png".
    assert detectar_tipo_imagen(b"<svg onload='alert(1)'/>") is None


def test_el_limite_de_tamano_es_5_mb():
    assert TAMANO_MAXIMO_FOTO_BYTES == 5 * 1024 * 1024


def test_la_ruta_de_la_foto_es_interna_y_por_id():
    assert ruta_foto("abc") == "/api/activos/abc/foto"
