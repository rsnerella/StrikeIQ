#!/usr/bin/env python3
"""
Script to get Upstox access token
Run this script and follow the instructions to get your access token
"""

import webbrowser
import urllib.parse

def get_auth_url():
    """Generate the Upstox authorization URL"""
    api_key = "53c878a9-3f5d-44f9-aa2d-2528d34a24cd"
    redirect_uri = "http://localhost:8000/api/v1/auth/upstox/callback"
    
    # Build the authorization URL
    auth_url = (
        "https://api.upstox.com/v2/login/authorization/dialog?"
        f"response_type=code&"
        f"client_id={api_key}&"
        f"redirect_uri={urllib.parse.quote(redirect_uri)}"
    )
    
    return auth_url

def main():
    print("=== StrikeIQ Upstox Token Setup ===")
    print("\n1. Opening Upstox authorization page in your browser...")
    print("2. Login to your Upstox account")
    print("3. Authorize the application")
    print("4. After authorization, you'll be redirected to a callback URL")
    print("5. Copy the 'code' parameter from the callback URL")
    print("\n" + "="*50)
    
    auth_url = get_auth_url()
    print(f"\nAuthorization URL:\n{auth_url}")
    
    # Open in browser
    try:
        webbrowser.open(auth_url)
        print("\n✅ Browser opened successfully")
    except Exception as e:
        print(f"\n❌ Could not open browser: {e}")
        print("Please manually open the URL above in your browser")
    
    print("\n" + "="*50)
    print("After authorization, your callback URL will look like:")
    print("http://localhost:8000/api/v1/auth/upstox/callback?code=YOUR_CODE_HERE")
    print("\nCopy the YOUR_CODE_HERE part and run:")
    print("python exchange_upstox_token.py YOUR_CODE_HERE")

if __name__ == "__main__":
    main()
