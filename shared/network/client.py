import socket
import hmac
import hashlib
import json
import time
from typing import Dict, Any

class SecureTransportClient:
    """
    Python client for Android's SecureTransportServer.
    Handles length-prefixed framing, HMAC-SHA256 handshake, and request signature verification.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 50051, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.sock = None
        self.session_id = None
        self.sequence_number = 0
        self.token = None

    def connect(self) -> None:
        """
        Establishes raw TCP socket connection.
        """
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.host, self.port))

    def authenticate(self, token: str) -> bool:
        """
        Executes the initial authenticated connection handshake.
        """
        self.token = token
        timestamp = int(time.time() * 1000)
        
        # Calculate signature: HMAC-SHA256("AUTHENTICATE" + token + timestamp) using token as key
        content_to_sign = f"AUTHENTICATE{token}{timestamp}"
        signature = self._calculate_hmac_sha256(content_to_sign, token)

        handshake_payload = {
            "command": "AUTHENTICATE",
            "token": token,
            "timestamp": timestamp,
            "signature": signature
        }

        self._write_frame(json.dumps(handshake_payload))
        
        response_str = self._read_frame()
        if not response_str:
            raise ConnectionError("Empty handshake response from device")

        response = json.loads(response_str)
        if response.get("status") == "AUTHENTICATED":
            self.session_id = response.get("sessionId")
            self.sequence_number = 0
            return True
        else:
            raise PermissionError(f"Authentication failed: {response.get('message', 'Unknown error')}")

    def send_command(self, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Constructs, signs, and sends a validated command packet.
        """
        if not self.session_id:
            raise PermissionError("Client is not authenticated. Call authenticate() first.")

        params = params or {}
        self.sequence_number += 1
        timestamp = int(time.time() * 1000)

        # Build request envelope
        request = {
            "command": command,
            "sessionId": self.session_id,
            "sequenceNumber": self.sequence_number,
            "timestamp": timestamp
        }
        for k, v in params.items():
            request[k] = v

        # Calculate payload signature
        request["signature"] = self.calculate_payload_signature(request, self.token)

        self._write_frame(json.dumps(request))
        
        response_str = self._read_frame()
        if not response_str:
            raise ConnectionError("Empty response from device")

        return json.loads(response_str)

    def close(self) -> None:
        """
        Closes socket connection gracefully.
        """
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
        self.session_id = None

    def calculate_payload_signature(self, payload: Dict[str, Any], secret_key: str) -> str:
        """
        Format payload keys alphabetically as 'key=value;' and sign using HMAC-SHA256.
        """
        sorted_keys = sorted([k for k in payload.keys() if k != "signature"])
        parts = []
        for key in sorted_keys:
            parts.append(f"{key}={payload[key]};")
        data_to_sign = "".join(parts)
        return self._calculate_hmac_sha256(data_to_sign, secret_key)

    def _calculate_hmac_sha256(self, data: str, key: str) -> str:
        return hmac.new(
            key.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _write_frame(self, payload: str) -> None:
        payload_bytes = payload.encode("utf-8")
        length = len(payload_bytes)
        # 4-byte big-endian length prefix header
        header = length.to_bytes(4, byteorder="big")
        self.sock.sendall(header + payload_bytes)

    def _read_frame(self) -> str:
        # Read 4-byte length header
        header = self._recv_all(4)
        if not header:
            return ""
        length = int.from_bytes(header, byteorder="big")
        if length <= 0 or length > 10 * 1024 * 1024:
            raise ValueError(f"Invalid frame length received: {length}")
        
        payload_bytes = self._recv_all(length)
        if not payload_bytes:
            return ""
        return payload_bytes.decode("utf-8")

    def _recv_all(self, length: int) -> bytes:
        data = b""
        while len(data) < length:
            chunk = self.sock.recv(length - len(data))
            if not chunk:
                return b""
            data += chunk
        return data
