/**
 * Shared Type Definitions for Phoenix Backup
 * Sprint 1 Specifications
 */

export interface ParsedDevice {
  deviceId: string;
  manufacturer: string;
  model: string;
  androidVersion: string;
  apiLevel: number;
}

export type DeviceStatus = 'CONNECTED' | 'UNAUTHORIZED' | 'DISCONNECTED';

export interface AdbConnectionUpdate {
  status: DeviceStatus;
  device: ParsedDevice | null;
  adbError?: string | null;
}

export interface KeyDerivationRequest {
  passphrase: string;
  salt?: string;
}

export interface KeyDerivationResponse {
  success: boolean;
  keyHex?: string;
  saltHex?: string;
  error?: string;
}

export interface IpcResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

declare global {
  interface Window {
    electronAPI: {
      onDeviceStateChange: (callback: (event: any, data: AdbConnectionUpdate) => void) => void;
      derivePassphraseKey: (request: KeyDerivationRequest) => Promise<IpcResponse<KeyDerivationResponse>>;
      retryDeviceConnection: () => Promise<IpcResponse<any>>;
      getCurrentDeviceState: () => Promise<IpcResponse<AdbConnectionUpdate>>;
      getSettings: () => Promise<IpcResponse<any>>;
      saveSettings: (settings: any) => Promise<IpcResponse<any>>;
      runAssessment: (serial: string, overrides: string[]) => Promise<IpcResponse<any>>;
      exportHtmlReport: () => Promise<IpcResponse<string>>;
      exportPdfReport: () => Promise<IpcResponse<string>>;
      onAssessmentLog: (callback: (event: any, log: string) => void) => void;
      getExtractionLogs: (jobId: string) => Promise<IpcResponse<any>>;
      runBackup: (serial: string, token: string) => Promise<IpcResponse<any>>;
      onBackupLog: (callback: (event: any, log: string) => void) => void;
    };
  }
}
