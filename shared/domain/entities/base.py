from pydantic import BaseModel, ConfigDict


class BaseDomainEntity(BaseModel):
    """Base class for entities and value objects in the domain."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
