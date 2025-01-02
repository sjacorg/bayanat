from typing import Optional
from pydantic import BaseModel, Field


class UserCompactModel(BaseModel):
    id: int
    name: Optional[str] = Field(default=None, max_length=255)
    username: Optional[str] = Field(default=None, max_length=255)
    active: bool = Field(default=False)


class RoleModel(BaseModel):
    id: int
    name: Optional[str] = Field(default=None, max_length=80)
    color: Optional[str] = Field(default=None, max_length=10)
    description: Optional[str]


class UserItemModel(BaseModel):
    id: int
    name: Optional[str] = Field(max_length=255)
    google_id: Optional[str] = Field(max_length=255)
    email: Optional[str] = Field(max_length=255)
    username: Optional[str] = Field(max_length=255)
    active: bool = Field(default=False)
    roles: Optional[list[RoleModel]] = Field(default_factory=list)
    view_usernames: Optional[bool] = Field(default=True)
    view_simple_history: Optional[bool] = Field(default=True)
    view_full_history: Optional[bool] = Field(default=True)
    can_self_assign: Optional[bool] = Field(default=False)
    can_edit_locations: Optional[bool] = Field(default=False)
    can_export: Optional[bool] = Field(default=False)
    force_reset: Optional[str] = None
