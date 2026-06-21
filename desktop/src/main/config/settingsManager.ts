import { app } from 'electron';
import * as path from 'path';
import * as fs from 'fs';

export interface SystemSettings {
  backupDir: string;
  customAdbPath: string;
  derivationProfile: 'standard' | 'enhanced' | 'paranoid';
}

const DEFAULT_SETTINGS: SystemSettings = {
  backupDir: '',
  customAdbPath: '',
  derivationProfile: 'standard'
};

function getSettingsPath(): string {
  return path.join(app.getPath('userData'), 'config.json');
}

export function loadSettings(): SystemSettings {
  try {
    // Lazy-load default backup directory based on documents folder
    if (!DEFAULT_SETTINGS.backupDir) {
      try {
        DEFAULT_SETTINGS.backupDir = path.join(app.getPath('documents'), 'PhoenixBackups');
      } catch {
        DEFAULT_SETTINGS.backupDir = path.join(app.getPath('home'), 'PhoenixBackups');
      }
    }

    const configPath = getSettingsPath();
    if (fs.existsSync(configPath)) {
      const rawData = fs.readFileSync(configPath, 'utf8');
      const parsed = JSON.parse(rawData);
      return { ...DEFAULT_SETTINGS, ...parsed };
    }
  } catch (err) {
    console.error('[SettingsManager] Failed to load config:', err);
  }
  return { ...DEFAULT_SETTINGS };
}

export function saveSettings(settings: SystemSettings): boolean {
  try {
    const configPath = getSettingsPath();
    const dir = path.dirname(configPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(configPath, JSON.stringify(settings, null, 2), 'utf8');
    console.log('[SettingsManager] Settings saved successfully to:', configPath);
    return true;
  } catch (err) {
    console.error('[SettingsManager] Failed to save config:', err);
    return false;
  }
}
