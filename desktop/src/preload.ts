import { contextBridge, ipcRenderer } from 'electron';
import { AdbConnectionUpdate, KeyDerivationRequest } from '@phoenix/shared/types';

/**
 * Preload IPC Context Bridge mapping safe bindings from renderer context to Node main process.
 * TODO: Keep this file secure by explicitly declaring and sanitizing channel events.
 */
contextBridge.exposeInMainWorld('electronAPI', {
  /**
   * Listen for device connection status events pushed from main process.
   */
  onDeviceStateChange: (callback: (event: any, data: AdbConnectionUpdate) => void) => {
    ipcRenderer.on('device:state-change', (event, value) => callback(event, value));
  },

  /**
   * Request Argon2id password key derivation in main process worker.
   */
  derivePassphraseKey: (request: KeyDerivationRequest) => {
    return ipcRenderer.invoke('crypto:derive-key', request);
  },

  /**
   * Request manual retry of device connection scanning.
   */
  retryDeviceConnection: () => {
    return ipcRenderer.invoke('device:retry-connection');
  },

  /**
   * Query the last known device connection state.
   */
  getCurrentDeviceState: () => {
    return ipcRenderer.invoke('device:get-current-state');
  },

  /**
   * Fetch system configuration settings.
   */
  getSettings: () => {
    return ipcRenderer.invoke('settings:get');
  },

  /**
   * Save updated system settings.
   */
  saveSettings: (settings: any) => {
    return ipcRenderer.invoke('settings:save', settings);
  },

  /**
   * Run the pre-flight recovery assessment pipeline.
   */
  runAssessment: (serial: string, overrides: string[]) => {
    return ipcRenderer.invoke('assessment:run', serial, overrides);
  },

  /**
   * Export recovery HTML report.
   */
  exportHtmlReport: () => {
    return ipcRenderer.invoke('report:export-html');
  },

  /**
   * Export recovery PDF report.
   */
  exportPdfReport: () => {
    return ipcRenderer.invoke('report:export-pdf');
  },

  /**
   * Listen for real-time assessment logs.
   */
  onAssessmentLog: (callback: (event: any, log: string) => void) => {
    ipcRenderer.on('assessment:log', (event, value) => callback(event, value));
  },

  /**
   * Query database extraction logs for a job.
   */
  getExtractionLogs: (jobId: string) => {
    return ipcRenderer.invoke('db:get-extraction-logs', jobId);
  },

  /**
   * Run the secure data backup extraction pipeline.
   */
  runBackup: (serial: string, token: string) => {
    return ipcRenderer.invoke('backup:run', serial, token);
  },

  /**
   * Listen for real-time backup/extraction logs.
   */
  onBackupLog: (callback: (event: any, log: string) => void) => {
    ipcRenderer.on('backup:log', (event, value) => callback(event, value));
  }
});
