from __future__ import annotations

"""
Production Safe Upstox Token Manager
Handles OAuth login and Redis token storage
"""

import asyncio
import logging
import os
from typing import Optional, Dict, Any

import httpx
from fastapi import HTTPException

from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class TokenManager:

    def __init__(self):

        self._access_token: Optional[str] = os.getenv("UPSTOX_ACCESS_TOKEN")

        self._lock = asyncio.Lock()

    # ================= LOGIN =================

    async def login(self, code: str) -> Dict[str, Any]:

        url = "https://api.upstox.com/v2/login/authorization/token"

        payload = {
            "code": code,
            "client_id": os.getenv("UPSTOX_API_KEY"),
            "client_secret": os.getenv("UPSTOX_API_SECRET"),
            "redirect_uri": os.getenv("UPSTOX_REDIRECT_URI"),
            "grant_type": "authorization_code",
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        logger.info("Upstox OAuth code received")

        async with httpx.AsyncClient(timeout=10) as client:

            response = await client.post(url, data=payload, headers=headers)

        if response.status_code != 200:

            logger.error(f"Upstox token exchange failed: {response.text}")

            raise HTTPException(
                status_code=401,
                detail="Upstox token exchange failed"
            )

        data = response.json()

        token = data.get("access_token")

        if not token:

            raise HTTPException(
                status_code=401,
                detail="Access token missing from response"
            )

        await self.save_token(token)

        logger.info("Upstox token exchange success")

        return data

    async def force_refresh(self):
        """
        Force refresh Upstox token
        """
        logger.info("Forcing Upstox token refresh")
        return await self.get_token()

    # ================= TOKEN ACCESS =================

    async def get_token(self) -> Optional[str]:

        if self._access_token:
            return self._access_token

        try:

            token = await redis_client.get("upstox_access_token")

            if not token:
                logger.debug("No Upstox token available")
                return None

            if isinstance(token, bytes):
                token = token.decode()

            self._access_token = token

            logger.info("Upstox token loaded from Redis")

            return token

        except Exception as e:

            logger.warning(f"Redis token fetch failed: {e}")

            return None

    # ================= TOKEN SAVE =================

    async def save_token(self, token: str) -> None:

        async with self._lock:

            self._access_token = token

            try:

                await redis_client.setex(
                    "upstox_access_token",
                    3600,
                    token
                )

                logger.info("Upstox token saved to Redis")

            except Exception as e:

                logger.warning(f"Failed to save token to Redis: {e}")

    # ================= TOKEN DELETE =================

    async def delete_token(self) -> None:

        try:

            await redis_client.delete("upstox_access_token")

        except Exception as e:

            logger.warning(f"Redis delete failed: {e}")

        self._access_token = None

        logger.info("Upstox token removed")

    # ================= TOKEN VERIFY =================

    async def verify_token(self, token: str) -> bool:

        try:

            headers = {
                "Authorization": f"Bearer {token}"
            }

            async with httpx.AsyncClient(timeout=5) as client:

                r = await client.get(
                    "https://api.upstox.com/v2/user/profile",
                    headers=headers
                )

            if r.status_code == 200:

                logger.info("Upstox token valid")

                return True

            logger.warning(f"Upstox token invalid ({r.status_code})")

            return False

        except Exception as e:

            logger.error(f"Token verification error: {e}")

            return False

    # ================= TOKEN ENSURE =================

    async def ensure_token(self) -> Optional[str]:

        token = await self.get_token()

        if token:
            return token

        env_token = os.getenv("UPSTOX_ACCESS_TOKEN")

        if env_token:

            await self.save_token(env_token)

            logger.info("Token loaded from environment")

            return env_token

        logger.debug("No Upstox token available")

        return None

    async def get_valid_token(self) -> Optional[str]:
        """Compatibility method for older callers"""
        return await self.get_token()

    # ================= AUTH STATE =================

    def get_auth_state(self) -> Dict[str, Any]:

        return {
            "token_available": bool(self._access_token)
        }


# ================= SINGLETON =================

token_manager = TokenManager()


def get_token_manager() -> TokenManager:
    return token_manager