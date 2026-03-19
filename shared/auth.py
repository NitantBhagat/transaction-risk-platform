from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Sequence, Set

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from shared.config import get_base_settings
from shared.schemas.auth import RoleEnum, TokenPayload, UserContext


bearer_scheme = HTTPBearer(auto_error=False)


def decode_token(raw_token: str) -> TokenPayload:
    """
    Decode and validate a JWT access token into a typed payload.

    This is intentionally minimal and can be extended with additional
    validation and key management later.
    """
    settings = get_base_settings()

    options = {
        "verify_signature": True,
        "verify_exp": True,
        "verify_aud": settings.auth_audience is not None,
        "verify_iss": settings.auth_issuer is not None,
    }

    decoded = jwt.decode(
        raw_token,
        key=settings.auth_secret_key,
        algorithms=[settings.auth_algorithm],
        audience=settings.auth_audience,
        issuer=settings.auth_issuer,
        options=options,
    )
    return TokenPayload.model_validate(decoded)


def build_user_context(payload: TokenPayload) -> UserContext:
    roles: List[RoleEnum] = []
    for name in payload.roles:
        try:
            roles.append(RoleEnum(name))
        except ValueError:
            # Unknown role names are ignored rather than failing hard.
            continue

    issued_at: datetime | None = None
    if payload.iat is not None:
        issued_at = datetime.fromtimestamp(payload.iat, tz=timezone.utc)

    return UserContext(user_id=payload.sub, roles=roles, issued_at=issued_at)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> UserContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return build_user_context(payload)


def require_roles(required_roles: Sequence[RoleEnum]):
    """
    Build a dependency that enforces the presence of at least one required role.

    Usage:

        @router.get("/admin", dependencies=[Depends(require_roles([RoleEnum.ADMIN]))])
        async def admin_only(...):
            ...
    """
    required: Set[RoleEnum] = set(required_roles)

    async def dependency(user: UserContext = Depends(get_current_user)) -> UserContext:
        user_roles: Iterable[RoleEnum] = user.roles
        if not required.intersection(user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return dependency

