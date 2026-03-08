from __future__ import annotations
"""
Production-Grade Async Safe Token Manager
Handles single source of truth for Upstox access token
"""

import asyncio
import logging
import os
import httpx
import json
import requests
from typing import Optional, Dict, Any
from fastapi import HTTPException
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class AuthState:
    AUTHENTICATED = "authenticated"
    AUTH_REQUIRED = "auth_required"


class TokenManager:
    """
    Static token manager - handles OAuth login and token storage
    Upstox tokens do not support automatic refresh
    """

    def __init__(self):
        self._access_token = os.getenv("UPSTOX_ACCESS_TOKEN")
        self._lock = asyncio.Lock()

    async def login(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        """
        url = "https://api.upstox.com/v2/login/authorization/token"
        
        payload = {
            "code": code,
            "client_id": os.getenv("UPSTOX_API_KEY"),
            "client_secret": os.getenv("UPSTOX_API_SECRET"),
            "redirect_uri": os.getenv("UPSTOX_REDIRECT_URI"),
            "grant_type": "authorization_code"
        }
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=payload, headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=401,
                    detail="Upstox token exchange failed"
                )
            
            data = response.json()
            
            if "access_token" not in data:
                raise HTTPException(
                    status_code=401,
                    detail="No access token in response"
                )
            
            self._access_token = data["access_token"]
            
            # Store token in Redis for WebSocket services
            try:
                await redis_client.setex(
                    "upstox_access_token",
                    3600,  # 1 hour expiry
                    data["access_token"]
                )
                logger.info("Token stored in Redis")
            except Exception as e:
                logger.warning(f"Failed to store token in Redis: {e}")
            
            return data

    async def get_valid_token(self) -> str:
        """
        Returns access token or raises HTTPException
        """
        if self._access_token:
            return self._access_token
        
        try:
            token = await redis_client.get("upstox_access_token")
            if token:
                self._access_token = token
                logger.info("Token loaded from Redis")
                return token
        except Exception as e:
            logger.warning(f"Failed to load token from Redis: {e}")
        
        raise HTTPException(
            status_code=401,
            detail="Upstox not authenticated"
        )

    def get_auth_state(self) -> Dict[str, Any]:
        """
        Returns current authentication state
        """
        return {
            "token_available": bool(self._access_token)
        }

    async def verify_token(self, token: str) -> bool:
        """
        Verify token with Upstox API
        """
        try:
            headers = {
                "Authorization": f"Bearer {token}"
            }

            r = requests.get(
                "https://api.upstox.com/v2/user/profile",
                headers=headers,
                timeout=5
            )

            if r.status_code == 200:
                logger.info(" UPSTOX TOKEN VALID")
                return True

            logger.warning(f" UPSTOX TOKEN INVALID - Status: {r.status_code}")
            return False

        except Exception as e:
            logger.error(f" UPSTOX TOKEN VERIFICATION ERROR: {e}")
            return False

    async def get_token(self) -> Optional[str]:
        """
        Get token from Redis or memory
        """
        if self._access_token:
            return self._access_token
        
        try:
            token = await redis_client.get("upstox_access_token")
            if token:
                self._access_token = token
                logger.info("Token loaded from Redis")
                return token
        except Exception as e:
            logger.warning(f"Failed to load token from Redis: {e}")
        
        return None

    async def delete_token(self) -> None:
        """
        Delete token from Redis and memory
        """
        try:
            await redis_client.delete("upstox_access_token")
            logger.info(" TOKEN REMOVED FROM REDIS")
        except Exception as e:
            logger.warning(f"Failed to delete token from Redis: {e}")
        
        self._access_token = None
        logger.info(" TOKEN CLEARED FROM MEMORY")

    async def ensure_token(self):
        """
        Ensure Upstox token is available from Redis or environment
        """
        token = await self.get_token()

        if token:
            return token

        import os

        token = os.getenv("UPSTOX_ACCESS_TOKEN")

        if token:
            await self.save_token(token)
            logger.info("Upstox token loaded from environment and saved to Redis")
            return token

        logger.warning("No Upstox token available")
        return None

    async def save_token(self, token: str) -> None:
        """
        Save token to memory and Redis.
        """
        self._access_token = token
        try:
            await redis_client.setex(
                "upstox_access_token",
                3600,  # 1 hour expiry
                token
            )
            logger.info("Token saved to Redis")
        except Exception as e:
            logger.warning(f"Failed to save token to Redis: {e}")


# Global singleton instance
token_manager = TokenManager()

def get_token_manager() -> TokenManager:
    return token_manager