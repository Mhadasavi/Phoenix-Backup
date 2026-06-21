#!/usr/bin/env python3
import socket
import sys

# Mock ADB Server configurations
HOST = "127.0.0.1"
PORT = 5037  # Default ADB daemon port

def build_adb_response(payload: str) -> bytes:
    """
    Format standard ADB protocol response: OKAY + 4-hex-character length prefix + payload.
    """
    length_prefix = f"{len(payload):04x}"
    return b"OKAY" + length_prefix.encode("ascii") + payload.encode("utf8")

def start_mock_server():
    """
    Spawns the local socket server emulating adb daemon query handshakes.
    """
    print(f"[*] Starting Mock ADB server on {HOST}:{PORT}...")
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen(5)
        print("[*] Mock server listening. Press Ctrl+C to terminate.")
    except Exception as e:
        print(f"[!] Failed to bind server port: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        while True:
            client_conn, client_addr = server.accept()
            print(f"[+] Connection established from: {client_addr}")
            
            try:
                # Read 4-hex digit length header first
                header = client_conn.recv(4)
                if not header:
                    client_conn.close()
                    continue
                
                length = int(header.decode("ascii"), 16)
                request = client_conn.recv(length).decode("utf8")
                print(f"[<] Request received: {request}")

                # Handle mock device list queries
                if request == "host:devices":
                    # Simulate one connected device in authorized status
                    payload = "phoenix_emulator_serial\tdevice\n"
                    response = build_adb_response(payload)
                    client_conn.sendall(response)
                    print(f"[>] Replied: {response}")
                
                # Handle tracking queries
                elif request == "host:track-devices":
                    # Send OKAY header first
                    client_conn.sendall(b"OKAY")
                    # Send initial device list payload (length-prefixed)
                    payload = "phoenix_emulator_serial\tdevice\n"
                    length_prefix = f"{len(payload):04x}"
                    client_conn.sendall(length_prefix.encode("ascii") + payload.encode("utf8"))
                    print(f"[>] Started tracking. Initial list: {payload}")
                    
                    # Keep connection open until client closes it
                    try:
                        while True:
                            data = client_conn.recv(1024)
                            if not data:
                                break
                    except Exception:
                        pass
                
                # Handle connection queries
                elif "host:version" in request:
                    response = b"OKAY" + b"0004" + b"0028"  # ADB Version 40
                    client_conn.sendall(response)
                
                else:
                    # Fallback default response
                    client_conn.sendall(b"OKAY")
            
            except Exception as conn_err:
                print(f"[!] Connection handling error: {conn_err}")
            finally:
                client_conn.close()
                print("[-] Connection closed.")
                
    except KeyboardInterrupt:
        print("\n[*] Shutting down Mock ADB server. Exiting.")
    finally:
        server.close()

if __name__ == "__main__":
    start_mock_server()
