"""
Phoenix Backup ADB Wrapper Interface (Hardened Python Implementation)
"""

import logging
import shlex
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from .exceptions import (
    AdbException,
    AdbNotInstalledException,
    AdbDeviceNotFoundException,
    AdbDeviceUnauthorizedException,
    AdbSecurityException,
    AdbCommandExecutionException
)

# Configure module-level logger
logger = logging.getLogger("phoenix.adb")

# Whitelisted command executions to prevent shell injection (GAP-06)
COMMAND_WHITELIST = {"getprop", "pm", "stat", "find", "dumpsys", "du"}

@dataclass
class AdbDevice:
    serial: str
    status: str  # 'device', 'unauthorized', 'offline'
    model: Optional[str] = None

class AdbClientInterface(ABC):
    """
    Abstract Base Class defining the interface boundaries for ADB operations.
    Enables swapping implementations (e.g. CLI wrapping vs raw socket communication).
    """

    @abstractmethod
    def is_adb_available(self) -> bool:
        """Validates ADB daemon presence."""
        pass

    @abstractmethod
    def list_devices(self) -> List[AdbDevice]:
        """Lists connected Android devices in a lightweight scan."""
        pass

    @abstractmethod
    def get_device_property(self, serial: str, property_name: str) -> Optional[str]:
        """Lazy-loads system property from target device."""
        pass

    @abstractmethod
    def execute_shell_command(
        self,
        serial: str,
        command: str,
        args: Optional[List[str]] = None,
        timeout: int = 15
    ) -> str:
        """Executes a whitelisted shell command securely on target device."""
        pass

class AdbWrapper(AdbClientInterface):
    """
    CLI-based implementation of AdbClientInterface running ADB sub-processes.
    """

    def __init__(self, adb_path: Optional[str] = None):
        """
        Initializes the wrapper. Path checking and validation are deferred to runtime.
        """
        self._adb_path = adb_path
        self._resolved_binary: Optional[str] = None

    def _get_adb_binary(self) -> str:
        """
        Lazy-loads and resolves the adb binary path. Throws exception only on access.
        """
        if self._resolved_binary:
            return self._resolved_binary

        resolved = self._adb_path or shutil.which("adb")
        if not resolved:
            logger.error("ADB binary could not be found in system PATH during execution.")
            raise AdbNotInstalledException("The 'adb' command is not installed or not in PATH.")
        
        self._resolved_binary = resolved
        logger.debug("ADB binary path lazily resolved to: %s", self._resolved_binary)
        return self._resolved_binary

    def is_adb_available(self) -> bool:
        """
        Checks version query to validate ADB availability.
        """
        try:
            binary = self._get_adb_binary()
            result = subprocess.run(
                [binary, "version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                timeout=5
            )
            return result.returncode == 0
        except Exception as err:
            logger.debug("ADB availability check failed: %s", err)
            return False

    def list_devices(self) -> List[AdbDevice]:
        """
        Lightweight discovery scan of connected devices. Bypasses properties calls to scale (GAP-04).
        """
        logger.debug("Executing device discovery scan...") # Downgraded to debug to prevent polling logs spam
        try:
            binary = self._get_adb_binary()
            result = subprocess.run(
                [binary, "devices", "-l"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                timeout=10,
                check=True
            )
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error("ADB device list execution failed: %s", e)
            raise AdbException(f"Failed to query connected devices: {e}")

        devices = []
        lines = result.stdout.strip().split("\n")
        
        for line in lines[1:]:
            if not line.strip():
                continue
            
            parts = line.split()
            if len(parts) < 2:
                continue
            
            serial = parts[0]
            status = parts[1]
            model = None
            
            for part in parts[2:]:
                if part.startswith("model:"):
                    model = part.split(":")[1]
                elif part.startswith("device:") and not model:
                    model = part.split(":")[1]

            devices.append(AdbDevice(
                serial=serial,
                status=status,
                model=model
            ))
            
        logger.debug("Discovery completed. Detected %d devices.", len(devices))
        return devices

    def get_device_property(self, serial: str, property_name: str) -> Optional[str]:
        """
        Lazy-loads a property from build.prop.
        """
        logger.debug("Lazy-loading property '%s' for device [%s]", property_name, serial)
        try:
            binary = self._get_adb_binary()
            res = subprocess.run(
                [binary, "-s", serial, "shell", "getprop", property_name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                timeout=3
            )
            if res.returncode == 0:
                return res.stdout.strip()
            else:
                logger.debug("getprop command returned non-zero code %d for %s", res.returncode, property_name)
        except subprocess.SubprocessError as err:
            logger.debug("Failed to query device property '%s': %s", property_name, err)
        return None

    def execute_shell_command(
        self,
        serial: str,
        command: str,
        args: Optional[List[str]] = None,
        timeout: int = 15
    ) -> str:
        """
        Executes a whitelisted shell command on a specific device. Escapes arguments to prevent injection.
        """
        # Validate base binary is whitelisted (Security Auditing GAP-06)
        if command not in COMMAND_WHITELIST:
            logger.error("Execution blocked: command '%s' not in whitelisted registry", command)
            raise AdbSecurityException(f"Command '{command}' is blocked by whitelisting security policy.")

        # Validate target device status
        self._verify_device_status(serial)

        # Escape arguments to prevent injection
        escaped_args = [shlex.quote(arg) for arg in (args or [])]
        full_command = f"{command} " + " ".join(escaped_args)
        
        logger.info("Executing on device [%s]: %s", serial, full_command)
        
        try:
            binary = self._get_adb_binary()
            result = subprocess.run(
                [binary, "-s", serial, "shell", full_command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
        except subprocess.TimeoutExpired as err:
            logger.error("Command execution timed out on device [%s]: %s", serial, full_command)
            raise AdbException(f"Command execution timed out: {err}")
        except subprocess.SubprocessError as err:
            logger.error("Subprocess execution failure on device [%s]: %s", serial, err)
            raise AdbException(f"Subprocess call failed: {err}")

        if result.returncode != 0:
            combined_err = result.stderr.strip() or result.stdout.strip()
            logger.error("Command exited with status code %d: %s", result.returncode, combined_err)
            raise AdbCommandExecutionException(full_command, result.returncode, combined_err)

        return result.stdout

    def _verify_device_status(self, serial: str):
        """Helper to assert target device status is valid."""
        devices = self.list_devices()
        target = next((d for d in devices if d.serial == serial), None)
        
        if not target:
            raise AdbDeviceNotFoundException(f"Device with serial '{serial}' is not connected.")
        if target.status == "unauthorized":
            raise AdbDeviceUnauthorizedException(f"Device '{serial}' is unauthorized.")
        if target.status == "offline":
            raise AdbDeviceNotFoundException(f"Device '{serial}' is offline.")
