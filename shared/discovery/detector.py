"""
Phoenix Backup Device Discovery Module (Hardened Python Implementation)
"""

import logging
from dataclasses import dataclass
from typing import List, Optional
from shared.adb.wrapper import AdbClientInterface, AdbDevice
from shared.adb.exceptions import AdbException

# Configure module-level logger
logger = logging.getLogger("phoenix.discovery")

@dataclass
class StorageInfo:
    """Storage statistics parsed from target filesystem."""
    total_bytes: int
    used_bytes: int
    free_bytes: int

@dataclass
class AndroidDevice:
    """Detailed metadata mapping target Android devices."""
    serial: str
    status: str
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    android_version: Optional[str] = None
    api_level: Optional[int] = None
    storage: Optional[StorageInfo] = None

class DeviceDetector:
    """
    Service responsible for querying ADB connections, parsing metadata properties,
    and gathering device storage partitions stats.
    """

    def __init__(self, adb_client: AdbClientInterface):
        self.adb_client = adb_client

    def detect_devices(self) -> List[AndroidDevice]:
        """
        Scans for connected devices, loading properties and storage stats lazily
        only for authorized and active connections.
        """
        logger.info("Starting connected device scan and property extraction...")
        detected_devices: List[AndroidDevice] = []

        try:
            base_devices: List[AdbDevice] = self.adb_client.list_devices()
        except AdbException as err:
            logger.error("Failed to query base devices from adb client: %s", err)
            return []

        for base in base_devices:
            if base.status != "device":
                logger.warning("Device [%s] status is '%s'. Skipping metadata queries.", base.serial, base.status)
                detected_devices.append(AndroidDevice(
                    serial=base.serial,
                    status=base.status,
                    model=base.model
                ))
                continue

            # Query system properties lazily
            manufacturer = self.adb_client.get_device_property(base.serial, "ro.product.manufacturer")
            model = self.adb_client.get_device_property(base.serial, "ro.product.model") or base.model
            release = self.adb_client.get_device_property(base.serial, "ro.build.version.release")
            sdk_str = self.adb_client.get_device_property(base.serial, "ro.build.version.sdk")
            
            api_level = None
            if sdk_str and sdk_str.strip().isdigit():
                api_level = int(sdk_str)

            # Query storage stats using whitelisted 'stat' command (try /data then /sdcard fallback)
            storage = self._query_storage_stats(base.serial)

            device = AndroidDevice(
                serial=base.serial,
                status=base.status,
                manufacturer=manufacturer,
                model=model,
                android_version=release,
                api_level=api_level,
                storage=storage
            )
            logger.info("Successfully discovered and parsed device details: %s", device)
            detected_devices.append(device)

        return detected_devices

    def _query_storage_stats(self, serial: str) -> Optional[StorageInfo]:
        """
        Retrieves filesystem parameters from '/data' mount using whitelisted 'stat' call.
        If '/data' is inaccessible, falls back to '/sdcard/'.
        """
        # Primary target partition
        target_paths = ["/data", "/sdcard"]
        
        for path in target_paths:
            logger.debug("Querying storage stats for device [%s] at '%s'...", serial, path)
            try:
                # stat -f -c "%b|%f|%S" maps: total_blocks|free_blocks|block_size
                output = self.adb_client.execute_shell_command(
                    serial=serial,
                    command="stat",
                    args=["-f", "-c", "%b|%f|%S", path]
                )
                
                cleaned = output.strip()
                parts = cleaned.split("|")
                if len(parts) != 3:
                    logger.debug("Unexpected stat output format at '%s': '%s'", path, cleaned)
                    continue
                
                # Hardened validation parsing block properties (prevent value conversion crashes)
                total_blocks = int(parts[0])
                free_blocks = int(parts[1])
                block_size = int(parts[2])

                # Bounds validation (prevent zero-division or negative storage metrics)
                if total_blocks <= 0 or free_blocks < 0 or block_size <= 0:
                    logger.debug("Invalid storage block bounds at '%s': total=%d, free=%d, size=%d", 
                                 path, total_blocks, free_blocks, block_size)
                    continue

                total_bytes = total_blocks * block_size
                free_bytes = free_blocks * block_size
                used_bytes = total_bytes - free_bytes

                logger.debug("Successfully resolved storage stats for [%s] at '%s'", serial, path)
                return StorageInfo(
                    total_bytes=total_bytes,
                    used_bytes=used_bytes,
                    free_bytes=free_bytes
                )
            except ValueError as val_err:
                logger.debug("Failed parsing numeric block stats at '%s': %s", path, val_err)
            except AdbException as adb_err:
                logger.debug("ADB command execution failed querying stats at '%s': %s", path, adb_err)
            except Exception as err:
                logger.debug("Unexpected system failure querying stats at '%s': %s", path, err)
        
        logger.warning("All partition storage queries failed for device [%s]", serial)
        return None
