import unittest
from unittest.mock import Mock
import json
import struct
from shared.network.client import SecureTransportClient

class TestSecureTransportClient(unittest.TestCase):

    def setUp(self):
        self.client = SecureTransportClient(host="127.0.0.1", port=50051)
        self.mock_socket = Mock()
        self.client.sock = self.mock_socket

    def test_calculate_payload_signature(self):
        payload = {
            "command": "GET_CONTACTS",
            "sequenceNumber": 1,
            "timestamp": 123456789
        }
        secret = "my_secret_token"
        sig = self.client.calculate_payload_signature(payload, secret)
        self.assertIsNotNone(sig)
        self.assertEqual(len(sig), 64) # SHA256 hex string is 64 chars

    def test_authenticate_success(self):
        # Setup mock socket receive behavior:
        # First 4 bytes = big endian length of response
        response = {
            "status": "AUTHENTICATED",
            "sessionId": "mock-session-id-123"
        }
        resp_bytes = json.dumps(response).encode("utf-8")
        resp_len_header = struct.pack(">I", len(resp_bytes))

        # Config recv to return header, then payload
        self.mock_socket.recv.side_effect = [resp_len_header, resp_bytes]

        success = self.client.authenticate("token123")
        self.assertTrue(success)
        self.assertEqual(self.client.session_id, "mock-session-id-123")
        self.assertEqual(self.client.sequence_number, 0)

    def test_authenticate_failure(self):
        response = {
            "status": "UNAUTHORIZED",
            "message": "Invalid credentials"
        }
        resp_bytes = json.dumps(response).encode("utf-8")
        resp_len_header = struct.pack(">I", len(resp_bytes))

        self.mock_socket.recv.side_effect = [resp_len_header, resp_bytes]

        with self.assertRaises(PermissionError):
            self.client.authenticate("wrong_token")

    def test_send_command_success(self):
        self.client.session_id = "sess-id"
        self.client.token = "tok"

        response = {
            "status": "SUCCESS",
            "data": "some_data"
        }
        resp_bytes = json.dumps(response).encode("utf-8")
        resp_len_header = struct.pack(">I", len(resp_bytes))

        self.mock_socket.recv.side_effect = [resp_len_header, resp_bytes]

        res = self.client.send_command("GET_CONTACTS", {"limit": 10})
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertEqual(res.get("data"), "some_data")
        self.assertEqual(self.client.sequence_number, 1)

if __name__ == "__main__":
    unittest.main()
