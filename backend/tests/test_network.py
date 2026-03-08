"""
Network connectivity test for Supabase
"""
import asyncio
import socket
import ssl
import sys
import os

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def test_dns_resolution():
    """Test DNS resolution for Supabase host"""
    try:
        # Extract host from DATABASE_URL
        db_url = settings.DATABASE_URL
        host_start = db_url.find('@') + 1
        host_end = db_url.find(':', host_start)
        host = db_url[host_start:host_end]
        
        print(f"Testing DNS resolution for: {host}")
        
        # Test DNS resolution
        ip = socket.gethostbyname(host)
        print(f"✅ DNS resolution successful: {host} -> {ip}")
        return True
        
    except socket.gaierror as e:
        print(f"❌ DNS resolution failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Network test failed: {e}")
        return False

def test_port_connectivity():
    """Test port 5432 connectivity"""
    try:
        db_url = settings.DATABASE_URL
        host_start = db_url.find('@') + 1
        host_end = db_url.find(':', host_start)
        host = db_url[host_start:host_end]
        
        print(f"Testing port 5432 connectivity to: {host}")
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, 5432))
        sock.close()
        
        if result == 0:
            print("✅ Port 5432 connectivity successful")
            return True
        else:
            print(f"❌ Port 5432 connectivity failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Port test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Supabase Network Connectivity Test ===")
    print(f"Database URL: {settings.DATABASE_URL.split('@')[0]}@***")
    
    dns_ok = test_dns_resolution()
    port_ok = test_port_connectivity()
    
    if dns_ok and port_ok:
        print("\n✅ Network connectivity test PASSED")
    else:
        print("\n❌ Network connectivity test FAILED")
        print("\nPossible causes:")
        print("1. Firewall blocking port 5432")
        print("2. DNS resolution issues")
        print("3. Supabase service down")
        print("4. Incorrect database URL")
