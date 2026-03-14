#!/usr/bin/env python3
"""
Script to exchange Upstox authorization code for access token
Usage: python exchange_upstox_token.py YOUR_AUTH_CODE
"""

import sys
import httpx
import os

async def exchange_code_for_token(code: str):
    """Exchange authorization code for access token"""
    
    # Load environment variables
    api_key = os.getenv("UPSTOX_API_KEY", "53c878a9-3f5d-44f9-aa2d-2528d34a24cd")
    api_secret = os.getenv("UPSTOX_API_SECRET", "db083c9gux")
    redirect_uri = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8000/api/v1/auth/upstox/callback")
    
    url = "https://api.upstox.com/v2/login/authorization/token"
    
    payload = {
        "code": code,
        "client_id": api_key,
        "client_secret": api_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    print(f"Exchanging code for token...")
    print(f"URL: {url}")
    print(f"Client ID: {api_key}")
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, data=payload, headers=headers)
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                
                if access_token:
                    print(f"\n✅ SUCCESS! Access token obtained:")
                    print(f"Access Token: {access_token}")
                    print(f"\nAdd this to your .env file:")
                    print(f"UPSTOX_ACCESS_TOKEN={access_token}")
                    print(f"\nToken expires in: {data.get('expires_in', 'Unknown')} seconds")
                    return access_token
                else:
                    print("❌ No access token in response")
                    return None
            else:
                print(f"❌ Token exchange failed: {response.text}")
                return None
                
    except Exception as e:
        print(f"❌ Error during token exchange: {e}")
        return None

def main():
    if len(sys.argv) != 2:
        print("Usage: python exchange_upstox_token.py YOUR_AUTH_CODE")
        print("Get your auth code by running: python get_upstox_token.py")
        sys.exit(1)
    
    auth_code = sys.argv[1]
    print(f"Using auth code: {auth_code}")
    
    import asyncio
    token = asyncio.run(exchange_code_for_token(auth_code))
    
    if token:
        print("\n🎉 Token setup complete!")
        print("Now restart your backend server with the updated .env file")
    else:
        print("\n💥 Token setup failed!")
        print("Please check your auth code and try again")

if __name__ == "__main__":
    main()
