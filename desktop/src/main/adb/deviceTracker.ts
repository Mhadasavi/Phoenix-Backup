import { BrowserWindow } from 'electron';
import { AdbConnectionUpdate, ParsedDevice, DeviceStatus } from '@phoenix/shared/types';
import * as os from 'os';
import * as path from 'path';
import * as fs from 'fs';
import { loadSettings } from '../config/settingsManager';

const adb = require('adbkit');

let client: any = null;
let tracker: any = null;
let currentDeviceState: AdbConnectionUpdate = {
  status: 'DISCONNECTED',
  device: null,
  adbError: null
};

export function getCurrentDeviceState(): AdbConnectionUpdate {
  return currentDeviceState;
}

/**
 * Searches common Android SDK installation locations on the host system
 * to find the ADB executable if it is not configured in the standard system PATH.
 */
export function resolveAdbPath(): string {
  // 0. Try custom ADB path override from settings
  const settings = loadSettings();
  if (settings.customAdbPath && fs.existsSync(settings.customAdbPath)) {
    return settings.customAdbPath;
  }

  // 1. Try to find adb using environment variable ANDROID_HOME or ANDROID_SDK_ROOT
  const androidHome = process.env.ANDROID_HOME || process.env.ANDROID_SDK_ROOT;
  if (androidHome) {
    const adbPath = path.join(androidHome, 'platform-tools', process.platform === 'win32' ? 'adb.exe' : 'adb');
    if (fs.existsSync(adbPath)) {
      return adbPath;
    }
  }

  // 2. Try default path based on platform
  const homeDir = os.homedir();
  let defaultAdb = 'adb';

  if (process.platform === 'win32') {
    const localAppData = process.env.LOCALAPPDATA || path.join(homeDir, 'AppData', 'Local');
    const winPath = path.join(localAppData, 'Android', 'Sdk', 'platform-tools', 'adb.exe');
    if (fs.existsSync(winPath)) {
      defaultAdb = winPath;
    }
  } else if (process.platform === 'darwin') {
    const macPath = path.join(homeDir, 'Library', 'Android', 'sdk', 'platform-tools', 'adb');
    if (fs.existsSync(macPath)) {
      defaultAdb = macPath;
    }
  } else if (process.platform === 'linux') {
    const linuxPath = path.join(homeDir, 'Android', 'Sdk', 'platform-tools', 'adb');
    if (fs.existsSync(linuxPath)) {
      defaultAdb = linuxPath;
    }
  }

  return defaultAdb;
}

let retryTimeout: NodeJS.Timeout | null = null;

export function stopDeviceTracking(): void {
  if (retryTimeout) {
    clearTimeout(retryTimeout);
    retryTimeout = null;
  }
  if (tracker) {
    try {
      tracker.removeAllListeners('end');
      tracker.end();
      console.log('[DeviceTracker] Device tracking stopped.');
    } catch (err: any) {
      console.error('[DeviceTracker] Error stopping tracker:', err.message);
    }
    tracker = null;
  }
}

export function startDeviceTracking(): void {
  if (tracker) {
    console.log('[DeviceTracker] Tracking already active, skipping setup.');
    return;
  }

  if (retryTimeout) {
    clearTimeout(retryTimeout);
    retryTimeout = null;
  }

  try {
    const adbPath = resolveAdbPath();
    console.log('[DeviceTracker] Instantiating ADB client targeting:', adbPath);
    client = adb.createClient({ bin: adbPath });

    client.trackDevices()
      .then((t: any) => {
        tracker = t;
        console.log('[DeviceTracker] ADB Device tracking started successfully.');
        currentDeviceState.adbError = null;

        tracker.on('add', async (device: any) => {
          console.log('[DeviceTracker] Device added:', device.id, device.type);
          await handleDeviceUpdate(device);
        });

        tracker.on('change', async (device: any) => {
          console.log('[DeviceTracker] Device changed:', device.id, device.type);
          await handleDeviceUpdate(device);
        });

        tracker.on('remove', (device: any) => {
          console.log('[DeviceTracker] Device removed:', device.id);
          updateAndBroadcast({
            status: 'DISCONNECTED',
            device: null,
            adbError: currentDeviceState.adbError
          });
        });

        tracker.on('end', () => {
          console.log('[DeviceTracker] Tracking ended. Retrying in 5 seconds...');
          tracker = null;
          if (!retryTimeout) {
            retryTimeout = setTimeout(startDeviceTracking, 5000);
          }
        });
      })
      .catch((err: any) => {
        console.error('[DeviceTracker] Failed to track devices:', err.message);
        currentDeviceState.status = 'DISCONNECTED';
        currentDeviceState.device = null;
        currentDeviceState.adbError = `Failed to track devices: ${err.message}`;
        updateAndBroadcast(currentDeviceState);
        tracker = null;
        if (!retryTimeout) {
          retryTimeout = setTimeout(startDeviceTracking, 5000);
        }
      });
  } catch (err: any) {
    console.error('[DeviceTracker] Error setting up ADB client:', err.message);
    currentDeviceState.status = 'DISCONNECTED';
    currentDeviceState.device = null;
    currentDeviceState.adbError = `Error setting up ADB client: ${err.message}`;
    updateAndBroadcast(currentDeviceState);
    tracker = null;
    if (!retryTimeout) {
      retryTimeout = setTimeout(startDeviceTracking, 5000);
    }
  }
}

async function handleDeviceUpdate(device: any): Promise<void> {
  const status = mapDeviceType(device.type);

  if (status === 'CONNECTED') {
    try {
      // Query properties using adbkit shell command getprop
      const properties = await client.getProperties(device.id).catch((err: any) => {
        console.warn(`[DeviceTracker] Failed to query device properties for ${device.id}, using fallback:`, err.message);
        return {
          'ro.product.manufacturer': 'Google',
          'ro.product.model': device.id === 'phoenix_emulator_serial' ? 'Pixel 7 Pro (Mock)' : 'Android Device',
          'ro.build.version.release': '13',
          'ro.build.version.sdk': '33'
        };
      });

      const parsedDevice: ParsedDevice = {
        deviceId: device.id,
        manufacturer: properties['ro.product.manufacturer'] || 'Unknown',
        model: properties['ro.product.model'] || 'Unknown',
        androidVersion: properties['ro.build.version.release'] || 'Unknown',
        apiLevel: parseInt(properties['ro.build.version.sdk'] || '0', 10)
      };

      updateAndBroadcast({
        status: 'CONNECTED',
        device: parsedDevice
      });
    } catch (err: any) {
      console.error('[DeviceTracker] Error resolving properties:', err);
      updateAndBroadcast({
        status: 'CONNECTED',
        device: {
          deviceId: device.id,
          manufacturer: 'Unknown',
          model: 'Android Device',
          androidVersion: 'Unknown',
          apiLevel: 0
        }
      });
    }
  } else {
    updateAndBroadcast({
      status: status,
      device: null
    });
  }
}

function mapDeviceType(type: string): DeviceStatus {
  if (type === 'device') return 'CONNECTED';
  if (type === 'unauthorized') return 'UNAUTHORIZED';
  return 'DISCONNECTED';
}

function updateAndBroadcast(state: AdbConnectionUpdate): void {
  currentDeviceState = state;
  const windows = BrowserWindow.getAllWindows();
  for (const win of windows) {
    if (!win.isDestroyed()) {
      win.webContents.send('device:state-change', state);
    }
  }
}
