from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CompanyCreate(BaseModel):
    legal_name: str = Field(min_length=1, max_length=300)
    display_name: str | None = Field(default=None, max_length=300)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    legal_name: str
    display_name: str | None
    country_code: str | None
    status: str
    sic_code: str | None
    sic_description: str | None
    sic_verified_at: datetime | None


class AssetCreate(BaseModel):
    company_id: UUID
    asset_type: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=300)


class AssetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID
    asset_type: str
    name: str
    status: str


class AssetIdentifierRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    company_id: UUID | None
    asset_id: UUID | None
    identifier_type: str
    value: str
    exchange_mic: str | None
    exchange_name: str | None
    valid_from: date | None
    valid_to: date | None
    verification_status: str
    source_name: str | None
    source_url: str | None


class AssetSearchResult(BaseModel):
    company: CompanyRead
    assets: list[AssetRead]
    identifiers: list[AssetIdentifierRead]
