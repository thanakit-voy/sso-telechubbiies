"""
Base schemas and common utilities.
"""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


# Slug validation pattern
SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for created_at and updated_at fields."""

    created_at: datetime
    updated_at: Optional[datetime] = None


class SlugMixin(BaseModel):
    """Mixin for slug validation."""

    @field_validator("slug", mode="before", check_fields=False)
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not v:
            raise ValueError("Slug cannot be empty")
        if not SLUG_PATTERN.match(v):
            raise ValueError("Slug must contain only letters, numbers, and underscores")
        if len(v) > 100:
            raise ValueError("Slug must be 100 characters or less")
        return v.lower()


class PaginationParams(BaseModel):
    """Common pagination parameters."""

    skip: int = 0
    limit: int = 50

    @field_validator("skip")
    @classmethod
    def validate_skip(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Skip must be non-negative")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Limit must be at least 1")
        if v > 100:
            return 100  # Cap at 100
        return v


class PaginatedResponse(BaseModel):
    """Base paginated response."""

    total: int
    skip: int
    limit: int


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class ErrorResponse(BaseModel):
    """Error response."""

    detail: str
    code: Optional[str] = None
