from shared.domain.errors import DomainError, ErrorCategory


def test_domain_error_expone_message_code_y_category_por_defecto():
    error = DomainError("algo salio mal")

    assert str(error) == "algo salio mal"
    assert error.message == "algo salio mal"
    assert error.code == "DOMAIN_ERROR"
    assert error.category == ErrorCategory.BUSINESS_RULE
    assert error.details == {}


def test_domain_error_permite_code_category_y_details_personalizados():
    error = DomainError(
        "conflicto",
        code="TAR-001",
        category=ErrorCategory.CONFLICT,
        details={"campo": "titulo"},
    )

    assert error.code == "TAR-001"
    assert error.category == ErrorCategory.CONFLICT
    assert error.details == {"campo": "titulo"}
