"""
Phoenix Backup ADB Module Exceptions
"""

class AdbException(Exception):
    """Base exception for all ADB abstraction layer errors."""
    pass

class AdbNotInstalledException(AdbException):
    """Raised when the adb binary is not found in the system path."""
    pass

class AdbDeviceNotFoundException(AdbException):
    """Raised when a specified device serial is not connected or offline."""
    pass

class AdbDeviceUnauthorizedException(AdbException):
    """Raised when the target device is unauthorized (USB debugging not allowed)."""
    pass

class AdbSecurityException(AdbException):
    """Raised when a command violates whitelisting or execution safety policies."""
    pass

class AdbCommandExecutionException(AdbException):
    """Raised when a command executed on the device return a non-zero exit code or fails."""
    def __init__(self, command: str, exit_code: int, stderr: str):
        super().__init__(f"Command '{command}' failed with exit code {exit_code}: {stderr}")
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr
