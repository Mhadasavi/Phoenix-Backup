"""
Phoenix Backup App Inventory Management Module (Hardened Python Implementation)
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional
from shared.adb.wrapper import AdbClientInterface
from shared.adb.exceptions import AdbException

# Configure module-level logger
logger = logging.getLogger("phoenix.inventory")

@dataclass
class AppInfo:
    """Structured model mapping an installed Android application."""
    app_name: str
    package_name: str
    version_name: Optional[str]
    version_code: Optional[int]
    apk_path: str
    is_system: bool

class AppInventoryManager:
    """
    Service responsible for querying application lists on Android devices,
    extracting package details, and parsing version statistics.
    """

    def __init__(self, adb_client: AdbClientInterface):
        self.adb_client = adb_client

    def get_installed_apps(self, serial: str, include_system: bool = False, fetch_versions: bool = False) -> List[AppInfo]:
        """
        Retrieves application inventory from the connected device.
        To ensure scalability and prevent event loop lag, 'fetch_versions' defaults to False.
        """
        logger.info("Crawling application inventory on device [%s] (fetch_versions=%s)...", serial, fetch_versions)
        apps: List[AppInfo] = []

        args = ["list", "packages", "-f"]
        if not include_system:
            args.append("-3")

        try:
            output = self.adb_client.execute_shell_command(
                serial=serial,
                command="pm",
                args=args
            )
        except AdbException as err:
            logger.error("Failed to query package list on device [%s]: %s", serial, err)
            return []

        lines = output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or not line.startswith("package:"):
                continue

            cleaned = line[len("package:"):]
            if "=" not in cleaned:
                logger.debug("Skipping unparsable package line: '%s'", line)
                continue
                
            parts = cleaned.rsplit("=", 1)
            apk_path = parts[0]
            package_name = parts[1]

            version_name = None
            version_code = None

            # Fetch versions only if explicitly requested (mitigates GAP child-process overhead)
            if fetch_versions:
                version_name, version_code = self.fetch_app_version(serial, package_name)
            
            is_system = self._is_system_package(apk_path)
            app_name = self._derive_app_name(package_name)

            app = AppInfo(
                app_name=app_name,
                package_name=package_name,
                version_name=version_name,
                version_code=version_code,
                apk_path=apk_path,
                is_system=is_system
            )
            logger.debug("Audited package: %s", app)
            apps.append(app)

        logger.info("Successfully audited %d packages on device [%s].", len(apps), serial)
        return apps

    def fetch_app_version(self, serial: str, package_name: str) -> tuple[Optional[str], Optional[int]]:
        """
        Queries package version metadata lazily using the whitelisted 'pm dump' command.
        """
        logger.debug("Lazy loading version details for package '%s' on [%s]...", package_name, serial)
        try:
            dump_output = self.adb_client.execute_shell_command(
                serial=serial,
                command="pm",
                args=["dump", package_name]
            )

            version_name = None
            version_code = None

            version_name_match = re.search(r"versionName=(\S+)", dump_output)
            if version_name_match:
                version_name = version_name_match.group(1).strip()

            version_code_match = re.search(r"versionCode=(\d+)", dump_output)
            if version_code_match:
                version_code = int(version_code_match.group(1).strip())

            return version_name, version_code
        except Exception as err:
            logger.debug("Failed parsing version stats for package '%s': %s", package_name, err)
            return None, None

    def _is_system_package(self, apk_path: str) -> bool:
        """Determines if a package is a system app based on partition path."""
        system_prefixes = ("/system/", "/vendor/", "/product/", "/apex/", "/system_ext/")
        return apk_path.startswith(system_prefixes)

    def _derive_app_name(self, package_name: str) -> str:
        """
        Derives formatted display name words from package name tokens.
        Replaces underscores/hyphens and title-cases results.
        """
        parts = package_name.split(".")
        if not parts:
            return package_name
        
        suffix = parts[-1]
        if suffix in ("android", "apps", "app") and len(parts) > 1:
            suffix = parts[-2]
            
        # Clean symbols (replace underscores/hyphens with spaces)
        cleaned = suffix.replace("_", " ").replace("-", " ")
        
        # Title case words (e.g. my app name -> My App Name)
        return cleaned.title()
