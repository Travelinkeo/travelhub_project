import socket
import sys


def check_tcp_connect():
    """Healthcheck: verifica que gunicorn acepte conexiones TCP."""
    HOST = "127.0.0.1"
    PORT = 8000
    try:
        s = socket.socket()
        s.settimeout(10)
        s.connect((HOST, PORT))
        s.close()
        sys.exit(0)
    except Exception:
        sys.exit(1)


if __name__ == "__main__":
    check_tcp_connect()
