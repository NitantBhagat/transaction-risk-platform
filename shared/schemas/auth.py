from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RoleEnum(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    SERVICE = "service"
    READONLY = "readonly"


class TokenPayload(BaseModel):
    sub: str = Field(..., description="Subject (user identifier)")
    roles: List[str] = Field(default_factory=list, description="List of role names")
    exp: Optional[int] = Field(default=None, description="Expiry as Unix timestamp")
    iat: Optional[int] = Field(default=None, description="Issued-at as Unix timestamp")
    iss: Optional[str] = Field(default=None, description="Token issuer")
    aud: Optional[str] = Field(default=None, description="Token audience")


class UserContext(BaseModel):
    user_id: str
    roles: List[RoleEnum]
    email: Optional[str] = None
    issued_at: Optional[datetime] = None

