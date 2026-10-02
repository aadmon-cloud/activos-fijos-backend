import pytest

from modules.movimientos.infrastructure.storage.disk_storage_repository import (
    DiskStorageRepository,
)


@pytest.fixture
def repo(tmp_path):
    return DiskStorageRepository(base_dir=str(tmp_path))


async def test_guardar_y_leer_devuelve_el_mismo_contenido(repo):
    ruta = await repo.guardar("pdfs/salidas", "archivo.pdf", b"contenido-de-prueba")

    contenido = await repo.leer(ruta)

    assert contenido == b"contenido-de-prueba"


async def test_guardar_crea_la_subcarpeta_si_no_existe(repo, tmp_path):
    await repo.guardar("pdfs/salidas", "archivo.pdf", b"x")

    assert (tmp_path / "pdfs" / "salidas" / "archivo.pdf").exists()


async def test_guardar_sanitiza_nombre_con_path_traversal(repo, tmp_path):
    ruta = await repo.guardar("pdfs/salidas", "../../etc/passwd", b"malicioso")

    # El nombre queda reducido a su basename — no escapa de la subcarpeta.
    assert ruta == "pdfs/salidas/passwd"
    assert (tmp_path / "pdfs" / "salidas" / "passwd").exists()
    assert not (tmp_path.parent / "etc").exists()


async def test_leer_rechaza_ruta_que_escapa_del_base_dir(repo):
    with pytest.raises(ValueError):
        await repo.leer("../../fuera_del_base.pdf")


async def test_leer_archivo_inexistente_lanza_file_not_found(repo):
    with pytest.raises(FileNotFoundError):
        await repo.leer("pdfs/salidas/no_existe.pdf")
