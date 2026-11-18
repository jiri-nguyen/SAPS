"""API schemas; JSON properties are camelCase (OpenAPI contract conventions)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from saps.domain.users import CurrentUser, Role


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class SessionCreate(CamelModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class UserAccount(CamelModel):
    id: UUID
    username: str
    display_name: str
    role: Role

    @classmethod
    def from_user(cls, user: CurrentUser) -> UserAccount:
        return cls(id=user.user_id, username=user.username, display_name=user.display_name, role=user.role)
