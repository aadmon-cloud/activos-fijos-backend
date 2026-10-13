from shared.domain.archivos import detectar_tipo_archivo


def test_detecta_jpeg():
    assert detectar_tipo_archivo(b"\xff\xd8\xff" + b"0" * 10) == "image/jpeg"


def test_detecta_png():
    assert detectar_tipo_archivo(b"\x89PNG\r\n\x1a\n" + b"0" * 10) == "image/png"


def test_detecta_webp():
    contenido = b"RIFF" + b"0000" + b"WEBP" + b"0" * 10
    assert detectar_tipo_archivo(contenido) == "image/webp"


def test_detecta_pdf():
    assert detectar_tipo_archivo(b"%PDF-1.4\n" + b"0" * 10) == "application/pdf"


def test_retorna_none_si_no_es_un_formato_soportado():
    assert detectar_tipo_archivo(b"no es un archivo soportado") is None


def test_no_confia_en_una_extension_falsa():
    # Un .txt con bytes que no coinciden con ninguna firma, aunque el nombre diga otra cosa.
    assert detectar_tipo_archivo(b"<script>alert(1)</script>") is None
