from typing import Any, Optional
from pydantic import BaseModel

from tests.models.user import UserCompactModel


class DataImportItemModel(BaseModel):
    class Config:
        anystr_strip_whitespace = True

    id: int
    table: str
    item_id: Optional[int] = None
    user: UserCompactModel
    file: Optional[str] = None
    file_format: Optional[str] = None
    file_hash: Optional[str] = None
    batch_id: Optional[str] = None
    status: str = "Pending"
    data: Optional[dict[str, Any]] = None
    log: Optional[str] = None
    updated_at: Optional[str] = None
    created_at: Optional[str] = None
    imported_at: Optional[str] = None


class DataImportResponseModel(BaseModel):
    items: list[DataImportItemModel]
    total: int
    perPage: int


class MediaPathItemModel(BaseModel):
    class Config:
        anystr_strip_whitespace = True

    filename: str
    path: str


class MediaFileModel(BaseModel):
    path: Optional[str]
    filename: Optional[str]


class EtlImportModel(BaseModel):
    files: list[MediaFileModel]
    mode: Optional[int]


class CsvImportResponseModel(BaseModel):
    etag: str
    filename: str
