from datetime import date, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.platform.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AssetType(StrEnum):
    COMMON_STOCK = "COMMON_STOCK"
    ADR = "ADR"
    ETF = "ETF"
    INDEX = "INDEX"
    REIT = "REIT"
    OTHER = "OTHER"


class EntityStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    PROVISIONAL = "PROVISIONAL"


class IdentifierType(StrEnum):
    CIK = "CIK"
    TICKER = "TICKER"
    ISIN = "ISIN"
    FIGI = "FIGI"
    LEI = "LEI"
    PROVIDER_ID = "PROVIDER_ID"


class VerificationStatus(StrEnum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    REJECTED = "REJECTED"


class Company(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_name", "legal_name"),
        Index("ix_companies_sic_code", "sic_code"),
        CheckConstraint(
            "sic_code IS NULL OR sic_code ~ '^[0-9]{4}$'",
            name="ck_companies_sic_code_format",
        ),
    )

    legal_name: Mapped[str] = mapped_column(String(300), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(300))
    country_code: Mapped[str | None] = mapped_column(String(2))
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EntityStatus.ACTIVE.value,
        server_default=EntityStatus.ACTIVE.value,
    )
    sic_code: Mapped[str | None] = mapped_column(String(4))
    sic_description: Mapped[str | None] = mapped_column(String(256))
    sic_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    assets: Mapped[list["Asset"]] = relationship(back_populates="company")
    identifiers: Mapped[list["AssetIdentifier"]] = relationship(back_populates="company")


class Asset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_company_type", "company_id", "asset_type"),
    )

    company_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=EntityStatus.ACTIVE.value,
        server_default=EntityStatus.ACTIVE.value,
    )

    company: Mapped[Company] = relationship(back_populates="assets")
    identifiers: Mapped[list["AssetIdentifier"]] = relationship(back_populates="asset")


class AssetIdentifier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "asset_identifiers"
    __table_args__ = (
        CheckConstraint(
            "(company_id IS NOT NULL AND asset_id IS NULL) OR "
            "(company_id IS NULL AND asset_id IS NOT NULL)",
            name="exactly_one_owner",
        ),
        CheckConstraint(
            "valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from",
            name="valid_date_order",
        ),
        UniqueConstraint(
            "identifier_type", "value", "valid_from",
            name="uq_asset_identifiers_type_value_from",
        ),
        Index("ix_asset_identifiers_lookup", "identifier_type", "value"),
    )

    company_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("companies.id", ondelete="RESTRICT")
    )
    asset_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT")
    )
    identifier_type: Mapped[str] = mapped_column(String(30), nullable=False)
    value: Mapped[str] = mapped_column(String(160), nullable=False)
    exchange_mic: Mapped[str | None] = mapped_column(String(4))
    exchange_name: Mapped[str | None] = mapped_column(String(120))
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    verification_status: Mapped[str] = mapped_column(
        String(30), nullable=False,
        default=VerificationStatus.UNVERIFIED.value,
        server_default=VerificationStatus.UNVERIFIED.value,
    )
    source_name: Mapped[str | None] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(String(500))

    company: Mapped[Company | None] = relationship(back_populates="identifiers")
    asset: Mapped[Asset | None] = relationship(back_populates="identifiers")
