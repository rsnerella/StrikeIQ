import logging
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import json
import os
import httpx
import urllib.parse
from fastapi import HTTPException
from ..core.config import settings
from ..models.database import AsyncSessionLocal
from ..models.system_config import SystemConfig
from sqlalchemy import select

logger = logging.getLogger(__name__)
_auth_service_instance = None


class UpstoxCredentials:
    def __init__(self, access_token: str, refresh_token: str, expires_in: int):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=expires_in or 3600
        )

    def is_expired(self) -> bool:
        # 60 second safety buffer
        return datetime.now(timezone.utc) >= (
            self.expires_at - timedelta(seconds=60)
        )


class UpstoxAuthService:

    def __init__(self, credentials_key: str = "upstox_auth_token"):
        self._credentials_key = credentials_key
        self._credentials: Optional[UpstoxCredentials] = None
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(timeout=10)

    # ================= AUTH URL =================
    def get_authorization_url(self):
        redirect_uri = os.getenv("UPSTOX_REDIRECT_URI")
        encoded_redirect = urllib.parse.quote(redirect_uri, safe='')
        return (
            f"https://api.upstox.com/v2/login/authorization/dialog"
            f"?response_type=code"
            f"&client_id={settings.UPSTOX_API_KEY}"
            f"&redirect_uri={encoded_redirect}"
        )

    # ================= LOAD =================
    async def _load_credentials(self) -> Optional[UpstoxCredentials]:
        """Load credentials from Supabase system_config table"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(SystemConfig).where(SystemConfig.key == self._credentials_key)
                result = await session.execute(stmt)
                config = result.scalar_one_or_none()
                
                if not config or not config.value:
                    return None
                
                data = config.value
                exp = datetime.fromisoformat(data["expires_at"])
                if exp.tzinfo is None:
                    exp = exp.replace(tzinfo=timezone.utc)

                creds = UpstoxCredentials(
                    data.get("access_token"),
                    data.get("refresh_token"),
                    0
                )
                creds.expires_at = exp
                return creds

        except Exception as e:
            logger.error(f"Failed to load credentials from DB: {e}")
            return None

    # ================= STORE =================
    async def _store_credentials(self, creds: UpstoxCredentials):
        """Store credentials in Supabase system_config table"""
        try:
            data = {
                "access_token": creds.access_token,
                "refresh_token": creds.refresh_token,
                "expires_at": creds.expires_at.isoformat()
            }
            
            async with AsyncSessionLocal() as session:
                stmt = select(SystemConfig).where(SystemConfig.key == self._credentials_key)
                result = await session.execute(stmt)
                config = result.scalar_one_or_none()
                
                if config:
                    config.value = data
                else:
                    config = SystemConfig(key=self._credentials_key, value=data)
                    session.add(config)
                
                await session.commit()
                
            self._credentials = creds
            logger.info("Upstox credentials stored safely in Supabase")
        except Exception as e:
            logger.error(f"Failed to store credentials in DB: {e}")

    # ================= EXCHANGE CODE =================
    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:

        async with self._lock:

            url = "https://api.upstox.com/v2/login/authorization/token"

            data = {
                "code": code,
                "client_id": settings.UPSTOX_API_KEY,
                "client_secret": settings.UPSTOX_API_SECRET,
                "redirect_uri": os.getenv("UPSTOX_REDIRECT_URI"),
                "grant_type": "authorization_code"
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            try:
                response = await self._client.post(url, headers=headers, data=data)
            except httpx.RequestError as e:
                logger.error(f"Network error: {e}")
                raise HTTPException(status_code=503, detail="Upstox unreachable")

            if response.status_code != 200:
                logger.error(f"Token exchange failed: {response.text}")
                raise HTTPException(status_code=401, detail="Token exchange failed")

            token = response.json()

            creds = UpstoxCredentials(
                token.get("access_token"),
                token.get("refresh_token"),
                token.get("expires_in") or 3600
            )

            await self._store_credentials(creds)

            return {
                "access_token": creds.access_token,
                "expires_in": token.get("expires_in") or 3600
            }

    # ================= TOKEN =================
    async def get_valid_token(self):
        """
        Returns a valid Upstox access token.
        Refreshes token if missing.
        """
        if not getattr(self, "access_token", None):
            await self.refresh_token()
        return self.access_token

    async def refresh_token(self):
        """
        Refresh Upstox access token.
        """
        self.access_token = os.getenv("UPSTOX_ACCESS_TOKEN")
        return self.access_token

    async def get_valid_access_token(self) -> Dict[str, Any]:

        async with self._lock:

            if not self._credentials:
                self._credentials = await self._load_credentials()

            if not self._credentials:
                raise HTTPException(status_code=401, detail="Authentication required")

            if self._credentials.is_expired():
                return await self._refresh_locked()

            return {
                "access_token": self._credentials.access_token,
                "expires_in": int(
                    (self._credentials.expires_at - datetime.now(timezone.utc)).total_seconds()
                )
            }

    # ================= REFRESH =================
    async def refresh_access_token(self) -> Dict[str, Any]:
        async with self._lock:
            return await self._refresh_locked()

    async def _refresh_locked(self) -> Dict[str, Any]:

        if not self._credentials or not self._credentials.refresh_token:
            raise HTTPException(status_code=401, detail="Authentication required")

        logger.info("Refreshing Upstox access token...")

        url = "https://api.upstox.com/v2/login/authorization/token"

        data = {
            "refresh_token": self._credentials.refresh_token,
            "client_id": settings.UPSTOX_API_KEY,
            "client_secret": settings.UPSTOX_API_SECRET,
            "redirect_uri": os.getenv("UPSTOX_REDIRECT_URI"),
            "grant_type": "refresh_token"
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        try:
            response = await self._client.post(url, headers=headers, data=data)
        except httpx.RequestError as e:
            logger.error(f"Network error during refresh: {e}")
            raise HTTPException(status_code=503, detail="Upstox unreachable")

        if response.status_code != 200:
            logger.error(f"Refresh failed: {response.text}")
            # Clear invalid credentials on 401
            if response.status_code == 401:
                await self._clear_credentials()
            raise HTTPException(status_code=401, detail="Authentication required")

        token_data = response.json()

        creds = UpstoxCredentials(
            token_data.get("access_token"),
            token_data.get("refresh_token") or self._credentials.refresh_token,
            token_data.get("expires_in") or 3600
        )

        await self._store_credentials(creds)

        logger.info("Token refreshed successfully")

        return {
            "access_token": creds.access_token,
            "expires_in": token_data.get("expires_in") or 3600
        }

    async def _clear_credentials(self):
        """
        Clear in-memory credentials and stored file
        """
        self._credentials = None
        # Clearing from DB is optional, but let's do it for security
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(SystemConfig).where(SystemConfig.key == self._credentials_key)
                result = await session.execute(stmt)
                config = result.scalar_one_or_none()
                if config:
                    await session.delete(config)
                    await session.commit()
                logger.info("Invalid credentials cleared from DB")
        except Exception as e:
            logger.error(f"Failed to clear credentials from DB: {e}")

    async def is_authenticated(self):
        """
        Check if we have valid credentials
        """
        if not self._credentials:
            self._credentials = await self._load_credentials()
        
        return (
            self._credentials is not None
            and self._credentials.refresh_token is not None
            and not self._credentials.is_expired()
        )

    async def close(self):
        await self._client.aclose()


def get_upstox_auth_service():
    global _auth_service_instance
    if _auth_service_instance is None:
        _auth_service_instance = UpstoxAuthService()
    return _auth_service_instance