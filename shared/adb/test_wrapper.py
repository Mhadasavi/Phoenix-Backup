"""
Unit tests for the Hardened ADB Abstraction Layer Wrapper module
"""

import unittest
from unittest.mock import patch, MagicMock
import subprocess

from .exceptions import (
    AdbNotInstalledException,
    AdbDeviceNotFoundException,
    AdbDeviceUnauthorizedException,
    AdbSecurityException,
    AdbCommandExecutionException
)
from .wrapper import AdbWrapper, AdbDevice


class TestAdbWrapper(unittest.TestCase):

    def test_constructor_no_side_effects(self):
        """
        Verify class instantiation does not call system utilities or throw exceptions.
        """
        # This should succeed even if adb is not in PATH or shutil fails
        wrapper = AdbWrapper(adb_path="/invalid/path/to/adb")
        self.assertIsNotNone(wrapper)

    @patch("shutil.which")
    def test_adb_binary_not_found_on_execution(self, mock_which):
        """
        Verify path checking raises exception only when executing command tasks.
        """
        mock_which.return_value = None
        wrapper = AdbWrapper()
        
        # Action triggers lazy-loading checks
        with self.assertRaises(AdbNotInstalledException):
            wrapper.list_devices()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_is_adb_available_success(self, mock_run, mock_which):
        """
        Verify available status is true if version query succeeds.
        """
        mock_which.return_value = "/usr/bin/adb"
        mock_run.return_value = MagicMock(returncode=0)
        
        wrapper = AdbWrapper()
        self.assertTrue(wrapper.is_adb_available())

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_list_devices_parsing_is_lightweight(self, mock_run, mock_which):
        """
        Verify list_devices parses targets without calling properties (lazy-loading).
        """
        mock_which.return_value = "/usr/bin/adb"
        
        # Mock adb devices -l output
        mock_stdout = (
            "List of devices attached\n"
            "emulator-5554          device product:sdk_phone_x86 model:sdk_phone_x86 device:generic_x86\n"
            "unauth-serial          unauthorized\n"
        )
        mock_devices_res = MagicMock(returncode=0, stdout=mock_stdout)
        mock_run.side_effect = [mock_devices_res]

        wrapper = AdbWrapper()
        devices = wrapper.list_devices()
        
        # Only 1 subprocess run should be executed (no manufacturer queries during scan)
        self.assertEqual(mock_run.call_count, 1)
        self.assertEqual(len(devices), 2)
        
        self.assertEqual(devices[0].serial, "emulator-5554")
        self.assertEqual(devices[0].status, "device")
        self.assertEqual(devices[0].model, "sdk_phone_x86")

        self.assertEqual(devices[1].serial, "unauth-serial")
        self.assertEqual(devices[1].status, "unauthorized")

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_get_device_property_lazy(self, mock_run, mock_which):
        """
        Verify device properties are queried successfully on demand.
        """
        mock_which.return_value = "/usr/bin/adb"
        mock_res = MagicMock(returncode=0, stdout="Samsung\n")
        mock_run.return_value = mock_res

        wrapper = AdbWrapper()
        val = wrapper.get_device_property("emulator-5554", "ro.product.manufacturer")
        
        self.assertEqual(val, "Samsung")
        mock_run.assert_called_once()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_execute_shell_command_whitelisting(self, mock_run, mock_which):
        """
        Verify whitelisting blocks execution of non-approved commands (GAP-06).
        """
        wrapper = AdbWrapper()
        
        # 'rm' is not in the whitelist registry
        with self.assertRaises(AdbSecurityException):
            wrapper.execute_shell_command("emulator-5554", "rm", ["-rf", "/"])

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_execute_shell_command_success(self, mock_run, mock_which):
        """
        Verify whitelisted command execution succeeds.
        """
        mock_which.return_value = "/usr/bin/adb"
        
        # Mock devices list query (verification step)
        mock_devices_res = MagicMock(
            returncode=0, 
            stdout="List of devices attached\nemulator-5554\tdevice\n"
        )
        
        # Mock whitelisted command (pm)
        mock_cmd_res = MagicMock(returncode=0, stdout="package:com.whatsapp\n")
        mock_run.side_effect = [mock_devices_res, mock_cmd_res]

        wrapper = AdbWrapper()
        # 'pm' is whitelisted
        out = wrapper.execute_shell_command("emulator-5554", "pm", ["list", "packages"])
        
        self.assertEqual(out, "package:com.whatsapp\n")
        self.assertEqual(mock_run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
