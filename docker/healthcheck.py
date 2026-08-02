"""Container healthcheck: the bundled proxy must accept connections."""

import os
import socket
import sys

if os.getenv("SPOOFDPI_ENABLED", "1") != "1":
    sys.exit(0)

# same address the entrypoint starts spoofdpi on
listen_addr = os.getenv("SPOOFDPI_LISTEN_ADDR", "127.0.0.1:8080")
host, _, port = listen_addr.rpartition(":")

try:
    with socket.create_connection((host, int(port)), timeout=3):
        pass
except OSError as e:
    print(f"proxy {listen_addr} unreachable: {e}")
    sys.exit(1)
