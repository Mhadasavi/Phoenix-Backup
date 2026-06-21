"""
Unit tests for the App Inventory module
"""

import unittest
from unittest.mock import MagicMock
from shared.adb.exceptions import AdbException
from .manager import AppInventoryManager, AppInfo


class TestAppInventoryManager(unittest.TestCase):

    def test_get_installed_apps_empty(self):
        """
        Verify empty list is returned if command fails or return empty lines.
        """
        mock_client = MagicMock()
        mock_client.execute_shell_command.return_value = ""

        manager = AppInventoryManager(mock_client)
        apps = manager.get_installed_apps("emulator-5554")

        self.assertEqual(len(apps), 0)
        mock_client.execute_shell_command.assert_called_once()

    def test_get_installed_apps_lazy_by_default(self):
        """
        Verify list query does NOT trigger version dumps by default (scalability).
        """
        mock_client = MagicMock()
        mock_list_output = "package:/data/app/com.whatsapp/base.apk=com.whatsapp\n"
        mock_client.execute_shell_command.return_value = mock_list_output

        manager = AppInventoryManager(mock_client)
        # Default fetch_versions is False
        apps = manager.get_installed_apps("emulator-5554")

        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].package_name, "com.whatsapp")
        self.assertIsNone(apps[0].version_name)
        self.assertIsNone(apps[0].version_code)
        
        # Verify only 1 adb execution was fired (no pm dumps during list query)
        self.assertEqual(mock_client.execute_shell_command.call_count, 1)

    def test_get_installed_apps_with_versions(self):
        """
        Verify package version info queries are parsed when requested.
        """
        mock_client = MagicMock()
        mock_list_output = "package:/data/app/com.whatsapp/base.apk=com.whatsapp\n"
        mock_whatsapp_dump = "versionName=2.24.10\nversionCode=241076000\n"
        mock_client.execute_shell_command.side_effect = [mock_list_output, mock_whatsapp_dump]

        manager = AppInventoryManager(mock_client)
        apps = manager.get_installed_apps("emulator-5554", fetch_versions=True)

        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].version_name, "2.24.10")
        self.assertEqual(apps[0].version_code, 241076000)
        self.assertEqual(mock_client.execute_shell_command.call_count, 2)

    def test_derive_app_name_formatting(self):
        """
        Verify package token names are clean-spaced and title-cased.
        """
        manager = AppInventoryManager(MagicMock())
        # Underscores
        self.assertEqual(manager._derive_app_name("com.company.my_backup_app"), "My Backup App")
        # Hyphens
        self.assertEqual(manager._derive_app_name("org.test-project.core-utility"), "Core Utility")
        # Standard
        self.assertEqual(manager._derive_app_name("com.whatsapp"), "Whatsapp")

    def test_is_system_package_paths(self):
        """
        Verify app categorization paths mapping.
        """
        manager = AppInventoryManager(MagicMock())
        self.assertTrue(manager._is_system_package("/system/app/Browser/Browser.apk"))
        self.assertTrue(manager._is_system_package("/vendor/app/OemSvc/OemSvc.apk"))
        self.assertFalse(manager._is_system_package("/data/app/~~a1b2/com.whatsapp/base.apk"))


if __name__ == "__main__":
    unittest.main()
