class FakeUnitOfWork:
    """Unidad de trabajo no-op para tests: no depende de Mongo real ni de sesiones."""

    session = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def fake_unit_of_work_factory():
    return FakeUnitOfWork()
