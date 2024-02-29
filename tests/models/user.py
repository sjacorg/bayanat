from typing import List, Optional
from pydantic import BaseModel, Field


class UserCompactModel(BaseModel):
    id: int
    name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, max_length=255)
    active: bool = Field(False)


class RoleModel(BaseModel):
    id: int
    name: Optional[str] = Field(None, max_length=80)
    color: Optional[str] = Field(None, max_length=10)
    description: Optional[str]


class UserItemModel(BaseModel):
    id: int
    name: Optional[str] = Field(..., max_length=255)
    google_id: Optional[str] = Field(..., max_length=255)
    email: Optional[str] = Field(..., max_length=255)
    username: Optional[str] = Field(..., max_length=255)
    active: bool = Field(False)
    roles: Optional[List[RoleModel]]
    view_usernames: Optional[bool] = Field(True)
    view_simple_history: Optional[bool] = Field(True)
    view_full_history: Optional[bool] = Field(True)
    can_self_assign: Optional[bool] = Field(False)
    can_edit_locations: Optional[bool] = Field(False)
    can_export: Optional[bool] = Field(False)
    force_reset: Optional[str]
