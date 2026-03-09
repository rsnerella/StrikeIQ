import socket

def check_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        try:
            s.connect((host, port))
            print(f"✅ Success: Connected to {host}:{port}")
        except Exception as e:
            print(f"❌ Error: Could not connect to {host}:{port} - {e}")

if __name__ == "__main__":
    check_port("127.0.0.1", 8000)
    check_port("localhost", 8000)
    check_port("0.0.0.0", 8000)
