"""
Unit tests for the Device Discovery module
"""

import unittest
from unittest.mock import MagicMock
from shared.adb.exceptions import AdbException
from shared.adb.wrapper import AdbDevice
from .detector import DeviceDetector, StorageInfo, AndroidDevice


class TestDeviceDetector(unittest.TestCase):

    def test_detect_no_devices_connected(self):
        """
        Verify detector returns empty list if no adb devices are detected.
        """
        mock_client = MagicMock()
        mock_client.list_devices.return_value = []
        
        detector = DeviceDetector(mock_client)
        devices = detector.detect_devices()
        
        self.assertEqual(len(devices), 0)
        mock_client.list_devices.assert_called_once()

    def test_detect_unauthorized_device_skips_properties(self):
        """
        Verify scanner skips properties and storage queries for unauthorized devices.
        """
        mock_client = MagicMock()
        # Mock connection list returning 1 unauthorized device
        mock_client.list_devices.return_value = [
            AdbDevice(serial="unauth-123", status="unauthorized", model="SM-G991B")
        ]

        detector = DeviceDetector(mock_client)
        devices = detector.detect_devices()

        self.assertEqual(len(devices), 1)
        dev = devices[0]
        
        self.assertEqual(dev.serial, "unauth-123")
        self.assertEqual(dev.status, "unauthorized")
        self.assertEqual(dev.model, "SM-G991B")
        
        # Ensure lazy loading skipped calls to getprop and shell execution
        self.assertIsNone(dev.manufacturer)
        self.assertIsNone(dev.storage)
        mock_client.get_device_property.assert_not_called()
        mock_client.execute_shell_command.assert_not_called()

    def test_detect_authorized_device_success(self):
        """
        Verify successful query sequence and storage calculation mapping.
        """
        mock_client = MagicMock()
        mock_client.list_devices.return_value = [
            AdbDevice(serial="emulator-5554", status="device", model="sdk_phone_x86")
        ]
        
        # Setup mock properties mapping
        mock_properties = {
            ("emulator-5554", "ro.product.manufacturer"): "Google",
            ("emulator-5554", "ro.product.model"): "Pixel 6",
            ("emulator-5554", "ro.build.version.release"): "13",
            ("emulator-5554", "ro.build.version.sdk"): "33"
        }
        mock_client.get_device_property.side_effect = lambda s, prop: mock_properties.get((s, prop))
        
        # Setup mock stat command output (total_blocks=1000, free_blocks=200, block_size=4096)
        mock_client.execute_shell_command.return_value = "1000|200|4096\n"

        detector = DeviceDetector(mock_client)
        devices = detector.detect_devices()

        self.assertEqual(len(devices), 1)
        dev = devices[0]

        self.assertEqual(dev.serial, "emulator-5554")
        self.assertEqual(dev.manufacturer, "Google")
        self.assertEqual(dev.model, "Pixel 6")
        self.assertEqual(dev.android_version, "13")
        self.assertEqual(dev.api_level, 33)
        
        # Validate storage stats conversion
        self.assertIsNotNone(dev.storage)
        self.assertEqual(dev.storage.total_bytes, 4096000)
        self.assertEqual(dev.storage.free_bytes, 819200)
        self.assertEqual(dev.storage.used_bytes, 3276800)

    def test_detect_storage_query_failover_success(self):
        """
        Verify that if /data query raises error, it falls back to /sdcard successfully.
        """
        mock_client = MagicMock()
        mock_client.list_devices.return_value = [
            AdbDevice(serial="emulator-5554", status="device")
        ]
        
        # First call (for /data) raises AdbException
        # Second call (for /sdcard) returns valid block sizes
        mock_client.execute_shell_command.side_effect = [
            AdbException("Access denied on /data"),
            "500|100|4096\n"
        ]

        detector = DeviceDetector(mock_client)
        devices = detector.detect_devices()
        
        self.assertEqual(len(devices), 1)
        dev = devices[0]
        
        self.assertIsNotNone(dev.storage)
        # Total bytes = 500 * 4096 = 2048000
        self.assertEqual(dev.storage.total_bytes, 2048000)
        self.assertEqual(dev.storage.free_bytes, 409600)
        self.assertEqual(mock_client.execute_shell_command.call_count, 2)

    def test_detect_storage_query_bounds_validation(self):
        """
        Verify that if total_blocks is negative or zero, it continues to failover or maps to None.
        """
        mock_client = MagicMock()
        mock_client.list_devices.return_value = [
            AdbDevice(serial="emulator-5554", status="device")
        ]
        
        # First call returns 0 total blocks (invalid)
        # Second call returns negative blocks (invalid)
        mock_client.execute_shell_command.side_effect = [
            "0|100|4096\n",
            "-500|100|4096\n"
        ]

        detector = DeviceDetector(mock_client)
        devices = detector.detect_devices()
        
        self.assertEqual(len(devices), 1)
        self.assertIsNone(devices[0].storage)


if __name__ == "__main__":
    unittest.main()
