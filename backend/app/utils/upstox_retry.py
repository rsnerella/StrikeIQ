from __future__ import annotations
import functools
import logging
from typing import Callable, TypeVar, Any, cast
from fastapi import HTTPException

from app.services.upstox_auth_service import get_upstox_auth_service

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry_on_upstox_401(func: F) -> F:
    """
    Retry exactly once on HTTP 401.
    Uses UpstoxAuthService.refresh_access_token()
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)

        except HTTPException as e:
            if e.status_code != 401:
                raise

            logger.warning(f"401 in {func.__name__} → refreshing token once")

            # refresh once
            auth_service = get_upstox_auth_service()
            await auth_service.refresh_access_token()

            logger.info(f"Retrying {func.__name__} after refresh")

            return await func(*args, **kwargs)

    return cast(F, wrapper)