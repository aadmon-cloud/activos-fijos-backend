from shared.domain.errors import DomainError, ErrorCategory


class AreaNombreDuplicadoError(DomainError):
    def __init__(self, nombre: str):
        super().__init__(
            f"Ya existe un area con el nombre '{nombre}'.",
            code="CAT-001",
            category=ErrorCategory.CONFLICT,
        )


class AreaNoEncontradaError(DomainError):
    def __init__(self, id_area: str):
        super().__init__(
            f"El area '{id_area}' no existe.",
            code="CAT-002",
            category=ErrorCategory.NOT_FOUND,
        )


class CategoriaNombreDuplicadaError(DomainError):
    def __init__(self, nombre: str):
        super().__init__(
            f"Ya existe una categoria con el nombre '{nombre}'.",
            code="CAT-003",
            category=ErrorCategory.CONFLICT,
        )


class CategoriaNoEncontradaError(DomainError):
    def __init__(self, id_categoria: str):
        super().__init__(
            f"La categoria '{id_categoria}' no existe.",
            code="CAT-004",
            category=ErrorCategory.NOT_FOUND,
        )


class CondicionNombreDuplicadoError(DomainError):
    def __init__(self, nombre: str):
        super().__init__(
            f"Ya existe una condicion con el nombre '{nombre}'.",
            code="CAT-005",
            category=ErrorCategory.CONFLICT,
        )


class CondicionNoEncontradaError(DomainError):
    def __init__(self, id_condicion: str):
        super().__init__(
            f"La condicion '{id_condicion}' no existe.",
            code="CAT-006",
            category=ErrorCategory.NOT_FOUND,
        )


class CondicionColorInvalidoError(DomainError):
    def __init__(self, color: str):
        super().__init__(
            f"El color '{color}' no tiene un formato hexadecimal valido (#RRGGBB).",
            code="CAT-007",
            category=ErrorCategory.VALIDATION,
        )


class SedeNombreDuplicadoError(DomainError):
    def __init__(self, nombre: str):
        super().__init__(
            f"Ya existe una sede con el nombre '{nombre}'.",
            code="CAT-008",
            category=ErrorCategory.CONFLICT,
        )


class SedeNoEncontradaError(DomainError):
    def __init__(self, id_sede: str):
        super().__init__(
            f"La sede '{id_sede}' no existe.",
            code="CAT-009",
            category=ErrorCategory.NOT_FOUND,
        )


class SedeEnUsoError(DomainError):
    def __init__(self, id_sede: str):
        super().__init__(
            f"La sede '{id_sede}' no se puede eliminar porque tiene lugares asociados.",
            code="CAT-010",
            category=ErrorCategory.CONFLICT,
        )


class LugarNombreDuplicadoError(DomainError):
    def __init__(self, nombre: str):
        super().__init__(
            f"Ya existe un lugar con el nombre '{nombre}' en esa sede.",
            code="CAT-011",
            category=ErrorCategory.CONFLICT,
        )


class LugarNoEncontradoError(DomainError):
    def __init__(self, id_lugar: str):
        super().__init__(
            f"El lugar '{id_lugar}' no existe.",
            code="CAT-012",
            category=ErrorCategory.NOT_FOUND,
        )


class AreaEnUsoError(DomainError):
    def __init__(self, id_area: str):
        super().__init__(
            f"El area '{id_area}' no se puede eliminar porque tiene activos asociados.",
            code="CAT-013",
            category=ErrorCategory.CONFLICT,
        )


class CategoriaEnUsoError(DomainError):
    def __init__(self, id_categoria: str):
        super().__init__(
            f"La categoria '{id_categoria}' no se puede eliminar porque tiene activos asociados.",
            code="CAT-014",
            category=ErrorCategory.CONFLICT,
        )


class CondicionEnUsoError(DomainError):
    def __init__(self, id_condicion: str):
        super().__init__(
            f"La condicion '{id_condicion}' no se puede eliminar porque tiene activos asociados.",
            code="CAT-015",
            category=ErrorCategory.CONFLICT,
        )


class LugarEnUsoError(DomainError):
    def __init__(self, id_lugar: str):
        super().__init__(
            f"El lugar '{id_lugar}' no se puede eliminar porque tiene activos asociados.",
            code="CAT-016",
            category=ErrorCategory.CONFLICT,
        )
