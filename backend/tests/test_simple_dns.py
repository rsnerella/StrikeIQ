"""
Simple DNS test for Supabase
"""
import socket

def test_supabase_dns():
    """Test basic Supabase DNS resolution"""
    try:
        # Test known Supabase host
        host = "db.yjxdepuwskcankmtfjvz.supabase.co"
        print(f"Testing DNS for: {host}")
        
        ip = socket.gethostbyname(host)
        print(f"✅ DNS successful: {host} -> {ip}")
        return True
        
    except Exception as e:
        print(f"❌ DNS failed: {e}")
        
        # Try alternative test
        try:
            print("Testing alternative: supabase.co")
            ip = socket.gethostbyname("supabase.co")
            print(f"✅ Alternative DNS successful: supabase.co -> {ip}")
            return True
        except Exception as e2:
            print(f"❌ Alternative DNS also failed: {e2}")
            return False

if __name__ == "__main__":
    print("=== DNS Test ===")
    test_supabase_dns()
