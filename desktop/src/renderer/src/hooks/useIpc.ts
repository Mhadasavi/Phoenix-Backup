import { useEffect, useState } from 'react';
import { AdbConnectionUpdate, DeviceStatus } from '@phoenix/shared/types';

/**
 * Custom React Hook to subscribe to system-level device connection updates.
 * TODO: Add offline error event handlers during Sprint 1.
 */
export function useDeviceState() {
  const [deviceState, setDeviceState] = useState<AdbConnectionUpdate>({
    status: 'DISCONNECTED',
    device: null
  });

  useEffect(() => {
    if (window.electronAPI && window.electronAPI.onDeviceStateChange) {
      window.electronAPI.onDeviceStateChange((event, data: AdbConnectionUpdate) => {
        setDeviceState(data);
      });
    }
  }, []);

  return deviceState;
}
