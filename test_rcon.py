#!/usr/bin/env python3
"""Test RCON connection to Minecraft server.

Usage:
    python test_rcon.py <host> <password> [port]

Example:
    python test_rcon.py 104.236.6.78 mypassword123
    python test_rcon.py 104.236.6.78 mypassword123 25575
"""

import sys
import time
from mcrcon import MCRcon


def test_with_mcrcon(host: str, password: str, port: int = 25575):
    """Test RCON using mcrcon library."""
    print(f"\n{'='*60}")
    print(f"Testing RCON with mcrcon library")
    print(f"{'='*60}")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Password: {'*' * len(password)} (length: {len(password)})")
    print(f"Password (actual): {password}")
    print()

    try:
        print("Opening connection...")
        with MCRcon(host, password, port=port, timeout=15) as mcr:
            print("✓ Connected successfully!")
            print()

            # Test a command
            print("Sending 'list' command...")
            response = mcr.command("list")
            print(f"✓ Response: {response}")
            print()

            # Test another command
            print("Sending 'help' command...")
            response = mcr.command("help")
            print(f"✓ Response (first 200 chars): {response[:200]}...")
            print()

            print("✓ RCON connection working perfectly!")
            return True

    except ConnectionRefusedError as e:
        print(f"✗ Connection refused: {e}")
        print(f"  → RCON port {port} is not listening")
        print(f"  → Check: ssh root@{host} 'ss -tlnp | grep {port}'")
        return False
    except TimeoutError as e:
        print(f"✗ Connection timeout: {e}")
        print(f"  → Server not responding on port {port}")
        print(f"  → Check firewall: ssh root@{host} 'ufw status | grep {port}'")
        return False
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        print(f"  → This might be an authentication failure")
        print(f"  → Check password: ssh root@{host} 'grep ^rcon\\. /opt/minecraft/server.properties'")
        return False


def test_raw_protocol(host: str, password: str, port: int = 25575):
    """Test RCON using raw socket protocol."""
    print(f"\n{'='*60}")
    print(f"Testing RCON with raw protocol")
    print(f"{'='*60}")

    import socket
    import struct

    # RCON packet types
    SERVERDATA_AUTH = 3
    SERVERDATA_AUTH_RESPONSE = 2
    SERVERDATA_EXECCOMMAND = 2
    SERVERDATA_RESPONSE_VALUE = 0

    def pack_packet(request_id: int, packet_type: int, payload: str) -> bytes:
        """Pack RCON packet."""
        payload_bytes = payload.encode("utf-8") + b"\x00\x00"
        packet_size = len(payload_bytes) + 8  # 4 (ID) + 4 (Type)
        return (
            struct.pack("<i", packet_size)
            + struct.pack("<ii", request_id, packet_type)
            + payload_bytes
        )

    def read_packet(sock: socket.socket) -> tuple[int, int, bytes]:
        """Read RCON packet."""
        # Read packet size
        size_data = sock.recv(4)
        if len(size_data) < 4:
            raise Exception(f"Failed to read packet size, got {len(size_data)} bytes")
        size = struct.unpack("<i", size_data)[0]

        # Read packet data
        packet_data = b""
        while len(packet_data) < size:
            chunk = sock.recv(size - len(packet_data))
            if not chunk:
                raise Exception("Connection closed while reading packet")
            packet_data += chunk

        request_id, packet_type = struct.unpack("<ii", packet_data[:8])
        payload = packet_data[8:-2]  # Remove trailing null bytes

        return request_id, packet_type, payload

    try:
        print(f"Opening socket to {host}:{port}...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)

        print("Connecting...")
        start = time.time()
        sock.connect((host, port))
        connect_time = time.time() - start
        print(f"✓ TCP connection established in {connect_time:.2f}s")
        print()

        # Send authentication
        print(f"Sending authentication packet...")
        auth_packet = pack_packet(1, SERVERDATA_AUTH, password)
        print(f"  Packet size: {len(auth_packet)} bytes")
        print(f"  Request ID: 1")
        print(f"  Packet type: {SERVERDATA_AUTH} (AUTH)")
        print(f"  Password: {password}")
        sock.send(auth_packet)
        print("✓ Auth packet sent")
        print()

        # Wait a moment
        print("Waiting 0.5s for server to process...")
        time.sleep(0.5)

        # Read response
        print("Reading authentication response...")
        try:
            req_id, pkt_type, payload = read_packet(sock)
            print(f"✓ Received packet:")
            print(f"  Request ID: {req_id}")
            print(f"  Packet type: {pkt_type}")
            print(f"  Payload: {payload}")
            print()

            if req_id == -1:
                print("✗ Authentication FAILED - password incorrect")
                sock.close()
                return False

            # Try to read second packet (some servers send two)
            try:
                sock.settimeout(2)
                req_id2, pkt_type2, payload2 = read_packet(sock)
                print(f"✓ Received second packet:")
                print(f"  Request ID: {req_id2}")
                print(f"  Packet type: {pkt_type2}")
                print()
            except socket.timeout:
                print("(No second packet - that's OK)")
                print()

            sock.settimeout(15)

            print("✓ Authentication successful!")
            print()

            # Send a command
            print("Sending 'list' command...")
            cmd_packet = pack_packet(2, SERVERDATA_EXECCOMMAND, "list")
            sock.send(cmd_packet)

            req_id, pkt_type, payload = read_packet(sock)
            print(f"✓ Command response: {payload.decode('utf-8')}")
            print()

            sock.close()
            print("✓ RCON working perfectly!")
            return True

        except socket.timeout:
            print("✗ Timeout waiting for authentication response")
            print("  → Server accepted connection but didn't respond")
            print("  → This usually means password mismatch (server silently drops)")
            sock.close()
            return False

    except ConnectionRefusedError as e:
        print(f"✗ Connection refused: {e}")
        print(f"  → Nothing listening on {host}:{port}")
        return False
    except socket.timeout as e:
        print(f"✗ Connection timeout: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    host = sys.argv[1]
    password = sys.argv[2]
    port = int(sys.argv[3]) if len(sys.argv) > 3 else 25575

    print("RCON Connection Test")
    print("=" * 60)
    print()
    print("This script tests RCON connectivity using two methods:")
    print("1. mcrcon library (high-level)")
    print("2. Raw socket protocol (low-level)")
    print()

    # Test with mcrcon
    success1 = test_with_mcrcon(host, password, port)

    # Test with raw protocol
    success2 = test_raw_protocol(host, password, port)

    # Summary
    print(f"\n{'='*60}")
    print("Summary")
    print(f"{'='*60}")
    print(f"mcrcon library: {'✓ PASS' if success1 else '✗ FAIL'}")
    print(f"Raw protocol:   {'✓ PASS' if success2 else '✗ FAIL'}")
    print()

    if not success1 and not success2:
        print("Both methods failed. Common issues:")
        print("1. Wrong password - check with:")
        print(f"   ssh root@{host} 'grep ^rcon\\. /opt/minecraft/server.properties'")
        print()
        print("2. RCON not listening on 0.0.0.0 - check with:")
        print(f"   ssh root@{host} 'ss -tlnp | grep {port}'")
        print(f"   Should show: 0.0.0.0:{port} (not 127.0.0.1:{port})")
        print()
        print("3. Server not running - check with:")
        print(f"   ssh root@{host} 'systemctl status minecraft'")
        sys.exit(1)
    elif success1 and not success2:
        print("mcrcon works but raw protocol fails - possible library differences")
        sys.exit(0)
    elif not success1 and success2:
        print("Raw protocol works but mcrcon fails - possible library issue")
        sys.exit(0)
    else:
        print("✓ All tests passed! RCON is working correctly.")
        sys.exit(0)


if __name__ == "__main__":
    main()
