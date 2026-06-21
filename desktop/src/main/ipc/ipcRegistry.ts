import { ipcMain, dialog, app, BrowserWindow } from 'electron';
import { KeyDerivationRequest, IpcResponse, KeyDerivationResponse } from '@phoenix/shared/types';
import { startDeviceTracking, stopDeviceTracking, getCurrentDeviceState, resolveAdbPath } from '../adb/deviceTracker';
import { loadSettings, saveSettings } from '../config/settingsManager';
import * as child_process from 'child_process';
import * as fs from 'fs';
import * as path from 'path';

/**
 * Register all Electron Main process IPC handlers (Adb, Database, Crypto workers).
 * TODO: Hook real business logic and error mapping wrappers during Sprint 1.
 */
export function registerIpcHandlers(): void {
  /**
   * Handle Argon2id Key Derivation requests.
   * Spawns worker thread to compute key hash asynchronously.
   */
  ipcMain.handle('crypto:derive-key', async (event, request: KeyDerivationRequest): Promise<IpcResponse<KeyDerivationResponse>> => {
    try {
      console.log('[IpcRegistry] Received Key Derivation request for passphrase');
      
      // TODO: Instantiate worker threads to derive key in the background
      const mockResponse: KeyDerivationResponse = {
        success: true,
        keyHex: '5ef812a83bd91209ca4583100234aefcc01934ba98efd23e120dca873491bcab',
        saltHex: '12ef43ba90dca8734fa98bc231ea4310'
      };

      return { success: true, data: mockResponse };
    } catch (error: any) {
      console.error('[IpcRegistry] Key derivation error:', error);
      return { success: false, error: error.message };
    }
  });

  /**
   * Handle request to manually retry/scan ADB device connections.
   */
  ipcMain.handle('device:retry-connection', async (): Promise<IpcResponse<any>> => {
    try {
      console.log('[IpcRegistry] Received manual request to retry device connection.');
      stopDeviceTracking();
      startDeviceTracking();
      return { success: true, data: getCurrentDeviceState() };
    } catch (error: any) {
      console.error('[IpcRegistry] Error retrying device connection:', error);
      return { success: false, error: error.message };
    }
  });

  /**
   * Handle request to query last known device connection state.
   */
  ipcMain.handle('device:get-current-state', async (): Promise<IpcResponse<any>> => {
    return { success: true, data: getCurrentDeviceState() };
  });

  /**
   * Handle request to fetch current system settings configuration.
   */
  ipcMain.handle('settings:get', async (): Promise<IpcResponse<any>> => {
    return { success: true, data: loadSettings() };
  });

  /**
   * Handle request to save updated system settings configuration.
   */
  ipcMain.handle('settings:save', async (event, settings: any): Promise<IpcResponse<any>> => {
    const success = saveSettings(settings);
    // Restart device tracking to apply any new custom ADB path override immediately
    if (success) {
      stopDeviceTracking();
      startDeviceTracking();
    }
    return { success };
  });

  /**
   * Run pre-flight assessment audit by spawning the Python CLI subprocess.
   */
  ipcMain.handle('assessment:run', async (event, serial: string, overrides: string[]): Promise<IpcResponse<any>> => {
    try {
      console.log('[IpcRegistry] Running diagnostic assessment for serial:', serial);
      const settings = loadSettings();
      const dbPath = path.join(app.getPath('userData'), 'phoenix_local.db');
      const backupDir = settings.backupDir;
      const adbPath = resolveAdbPath();

      if (!fs.existsSync(backupDir)) {
        fs.mkdirSync(backupDir, { recursive: true });
      }

      const scriptPath = path.resolve(app.getAppPath(), '..', 'tools', 'scripts', 'run_audit.py');
      console.log('[IpcRegistry] Python Script Path:', scriptPath);

      const pythonCmd = process.platform === 'win32' ? 'py' : 'python3';
      const args = [
        scriptPath,
        '--serial', serial,
        '--db', dbPath,
        '--output', backupDir,
        '--adb', adbPath
      ];

      if (overrides && overrides.length > 0) {
        args.push('--overrides', overrides.join(','));
      }

      console.log('[IpcRegistry] Spawning:', pythonCmd, args.join(' '));

      // Create a log file inside the backup directory to write stdout/stderr logs in real time (Sprint 2.5 logging support)
      const logFilePath = path.join(backupDir, 'phoenix_audit.log');
      const logStream = fs.createWriteStream(logFilePath, { flags: 'w' });
      logStream.write(`=== Diagnostics Assessment Start: ${new Date().toISOString()} ===\n`);
      logStream.write(`Command: ${pythonCmd} ${args.join(' ')}\n\n`);

      return new Promise<IpcResponse<any>>((resolve) => {
        const child = child_process.spawn(pythonCmd, args, {
          cwd: path.resolve(app.getAppPath(), '..')
        });

        let stdoutData = '';
        let stderrData = '';

        child.stdout.on('data', (data) => {
          const str = data.toString();
          stdoutData += str;
          logStream.write(str);

          // Broadcast real-time logs to the UI (Sprint 2.5 real-time console support)
          const windows = BrowserWindow.getAllWindows();
          for (const win of windows) {
            if (!win.isDestroyed()) {
              win.webContents.send('assessment:log', str);
            }
          }
        });

        child.stderr.on('data', (data) => {
          const str = data.toString();
          stderrData += str;
          logStream.write(str);

          // Broadcast real-time logs to the UI (Sprint 2.5 real-time console support)
          const windows = BrowserWindow.getAllWindows();
          for (const win of windows) {
            if (!win.isDestroyed()) {
              win.webContents.send('assessment:log', str);
            }
          }
        });

        child.on('error', (err) => {
          console.error('[IpcRegistry] Failed to start Python process:', err);
          logStream.write(`\nERROR spawning process: ${err.message}\n`);
          logStream.end();
          resolve({ success: false, error: `Failed to spawn Python process: ${err.message}. Check logs: ${logFilePath}` });
        });

        child.on('close', (code) => {
          console.log(`[IpcRegistry] Python process exited with code ${code}`);
          logStream.write(`\n=== Diagnostics Assessment Finished with exit code: ${code} at ${new Date().toISOString()} ===\n`);
          logStream.end();

          if (code !== 0) {
            resolve({
              success: false,
              error: `Python audit process exited with code ${code}. Check details in log file: ${logFilePath}`
            });
            return;
          }

          const lines = stdoutData.split('\n');
          let parsedResult = null;
          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('{"success":')) {
              try {
                parsedResult = JSON.parse(trimmed);
                break;
              } catch (e: any) {
                console.error('[IpcRegistry] JSON parse error on line:', trimmed, e);
              }
            }
          }

          if (parsedResult) {
            resolve({ success: true, data: parsedResult });
          } else {
            resolve({
              success: false,
              error: `Python completed but did not output structured audit JSON. Check logs: ${logFilePath}`
            });
          }
        });
      });
    } catch (error: any) {
      console.error('[IpcRegistry] Assessment run error:', error);
      return { success: false, error: error.message };
    }
  });

  /**
   * Export the generated HTML report.
   */
  ipcMain.handle('report:export-html', async (): Promise<IpcResponse<string>> => {
    try {
      const settings = loadSettings();
      const sourceFile = path.join(settings.backupDir, 'recovery_readiness_report.html');

      if (!fs.existsSync(sourceFile)) {
        return { success: false, error: 'Report file does not exist. Please run assessment first.' };
      }

      const win = BrowserWindow.getFocusedWindow();
      const { filePath } = await dialog.showSaveDialog(win!, {
        title: 'Export HTML Report',
        defaultPath: 'recovery_readiness_report.html',
        filters: [{ name: 'HTML Files', extensions: ['html'] }]
      });

      if (!filePath) {
        return { success: false, error: 'Export cancelled by user.' };
      }

      fs.copyFileSync(sourceFile, filePath);
      return { success: true, data: filePath };
    } catch (error: any) {
      console.error('[IpcRegistry] HTML Export error:', error);
      return { success: false, error: error.message };
    }
  });

  /**
   * Export the generated PDF report.
   */
  ipcMain.handle('report:export-pdf', async (): Promise<IpcResponse<string>> => {
    try {
      const settings = loadSettings();
      const sourceFile = path.join(settings.backupDir, 'recovery_readiness_report.pdf');

      if (!fs.existsSync(sourceFile)) {
        return { success: false, error: 'Report file does not exist. Please run assessment first.' };
      }

      const win = BrowserWindow.getFocusedWindow();
      const { filePath } = await dialog.showSaveDialog(win!, {
        title: 'Export PDF Report',
        defaultPath: 'recovery_readiness_report.pdf',
        filters: [{ name: 'PDF Files', extensions: ['pdf'] }]
      });

      if (!filePath) {
        return { success: false, error: 'Export cancelled by user.' };
      }

      fs.copyFileSync(sourceFile, filePath);
      return { success: true, data: filePath };
    } catch (error: any) {
      console.error('[IpcRegistry] PDF Export error:', error);
      return { success: false, error: error.message };
    }
  });

  /**
   * Fetch data extraction logs and statistics from local SQLite database.
   */
  ipcMain.handle('db:get-extraction-logs', async (event, jobId: string): Promise<IpcResponse<any[]>> => {
    try {
      const dbPath = path.join(app.getPath('userData'), 'phoenix_local.db');
      
      // Load better-sqlite3 dynamically to avoid compile blocker issues
      const Database = require('better-sqlite3');
      const db = new Database(dbPath);
      
      const rows = db.prepare(`
        SELECT data_type, status, records_extracted, timestamp 
        FROM job_extraction_logs 
        WHERE job_id = ?
      `).all(jobId);
      
      db.close();
      return { success: true, data: rows };
    } catch (error: any) {
      console.error('[IpcRegistry] Error fetching database extraction logs:', error);
      return { success: false, error: error.message };
    }
  });

  /**
   * Run full data backup and extraction by spawning the Python backup runner CLI.
   */
  ipcMain.handle('backup:run', async (event, serial: string, token: string): Promise<IpcResponse<any>> => {
    try {
      console.log('[IpcRegistry] Initiating full backup extraction for serial:', serial);
      const settings = loadSettings();
      const dbPath = path.join(app.getPath('userData'), 'phoenix_local.db');
      const backupDir = settings.backupDir;
      const adbPath = resolveAdbPath();

      if (!fs.existsSync(backupDir)) {
        fs.mkdirSync(backupDir, { recursive: true });
      }

      // 1. Start the Companion App foreground service and setup ADB Port Forwarding
      try {
        const startServiceCmd = `"${adbPath}" -s ${serial} shell am start-foreground-service -n com.phoenix.companion/.service.BackupService --es token ${token}`;
        console.log('[IpcRegistry] Starting companion foreground service:', startServiceCmd);
        child_process.execSync(startServiceCmd);

        const forwardCmd = `"${adbPath}" -s ${serial} forward tcp:58988 tcp:58988`;
        console.log('[IpcRegistry] Setting up ADB port forward:', forwardCmd);
        child_process.execSync(forwardCmd);
      } catch (tunnelError: any) {
        console.error('[IpcRegistry] Failed starting service or setting up ADB tunnel:', tunnelError);
        return { success: false, error: `Failed to start companion service or set up ADB tunnel: ${tunnelError.message}` };
      }

      // 2. Resolve script path and command args
      const scriptPath = path.resolve(app.getAppPath(), '..', 'tools', 'scripts', 'run_backup.py');
      const pythonCmd = process.platform === 'win32' ? 'py' : 'python3';
      const args = [
        scriptPath,
        '--serial', serial,
        '--db', dbPath,
        '--output', backupDir,
        '--token', token,
        '--port', '58988'
      ];

      console.log('[IpcRegistry] Spawning:', pythonCmd, args.join(' '));

      const logFilePath = path.join(backupDir, 'phoenix_backup.log');
      const logStream = fs.createWriteStream(logFilePath, { flags: 'w' });
      logStream.write(`=== Data Extraction Start: ${new Date().toISOString()} ===\n`);
      logStream.write(`Command: ${pythonCmd} ${args.join(' ')}\n\n`);

      return new Promise<IpcResponse<any>>((resolve) => {
        const child = child_process.spawn(pythonCmd, args, {
          cwd: path.resolve(app.getAppPath(), '..')
        });

        let stdoutData = '';
        let stderrData = '';

        child.stdout.on('data', (data) => {
          const str = data.toString();
          stdoutData += str;
          logStream.write(str);

          // Broadcast real-time logs to the UI
          const windows = BrowserWindow.getAllWindows();
          for (const win of windows) {
            if (!win.isDestroyed()) {
              win.webContents.send('backup:log', str);
            }
          }
        });

        child.stderr.on('data', (data) => {
          const str = data.toString();
          stderrData += str;
          logStream.write(str);

          // Broadcast real-time logs to the UI
          const windows = BrowserWindow.getAllWindows();
          for (const win of windows) {
            if (!win.isDestroyed()) {
              win.webContents.send('backup:log', str);
            }
          }
        });

        child.on('error', (err) => {
          console.error('[IpcRegistry] Failed to start Python backup process:', err);
          logStream.write(`\nERROR spawning process: ${err.message}\n`);
          logStream.end();
          resolve({ success: false, error: `Failed to spawn Python backup process: ${err.message}` });
        });

        child.on('close', (code) => {
          console.log(`[IpcRegistry] Python backup process exited with code ${code}`);
          logStream.write(`\n=== Data Extraction Finished with exit code: ${code} at ${new Date().toISOString()} ===\n`);
          logStream.end();

          if (code !== 0) {
            resolve({
              success: false,
              error: `Backup process exited with code ${code}. Check log details: ${logFilePath}`
            });
            return;
          }

          const lines = stdoutData.split('\n');
          let parsedResult = null;
          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('{"success":')) {
              try {
                parsedResult = JSON.parse(trimmed);
                break;
              } catch (e: any) {
                console.error('[IpcRegistry] JSON parse error on output line:', trimmed, e);
              }
            }
          }

          if (parsedResult) {
            resolve({ success: true, data: parsedResult });
          } else {
            resolve({
              success: false,
              error: `Backup completed but did not output structured job JSON. Check logs: ${logFilePath}`
            });
          }
        });
      });
    } catch (error: any) {
      console.error('[IpcRegistry] Backup handler crashed:', error);
      return { success: false, error: error.message };
    }
  });
}
