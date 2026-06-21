import { app, BrowserWindow } from 'electron';
import * as path from 'path';
import { DatabaseManager } from './db/database';
import { registerIpcHandlers } from './ipc/ipcRegistry';
import { startDeviceTracking, getCurrentDeviceState } from './adb/deviceTracker';

let mainWindow: BrowserWindow | null = null;

/**
 * Initialize Electron Main Process and spawn BrowserWindow context.
 * TODO: Configure window parameters and initialize discovery loops for Sprint 1.
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1024,
    height: 768,
    webPreferences: {
      preload: path.join(__dirname, '../preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Load the dashboard view
  mainWindow.loadFile(path.join(__dirname, '../../src/renderer/index.html'));

  // Broadcast current connection state once page loads
  mainWindow.webContents.on('did-finish-load', () => {
    const currentState = getCurrentDeviceState();
    if (mainWindow && currentState) {
      mainWindow.webContents.send('device:state-change', currentState);
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.on('ready', async () => {
  // Initialize Database manager migrations
  const dbManager = new DatabaseManager();
  const dbPath = path.join(app.getPath('userData'), 'phoenix_local.db');
  dbManager.initialize(dbPath);

  // Register Electron IPC handlers (Adb discovery, Cryptographic workers)
  registerIpcHandlers();

  // Start ADB device tracking discovery loop
  startDeviceTracking();

  // Create UI viewport context
  createWindow();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});
