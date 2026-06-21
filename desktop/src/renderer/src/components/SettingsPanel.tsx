import React, { useEffect, useState } from 'react';

/**
 * SettingsPanel - System Configuration Form for Phoenix Backup.
 */
export function SettingsPanel() {
  const [backupDir, setBackupDir] = useState('');
  const [customAdbPath, setCustomAdbPath] = useState('');
  const [derivationProfile, setDerivationProfile] = useState<'standard' | 'enhanced' | 'paranoid'>('standard');
  
  const [isSaving, setIsSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'success' | 'error' | null>(null);

  useEffect(() => {
    // Load existing settings config on mount
    if (window.electronAPI && window.electronAPI.getSettings) {
      window.electronAPI.getSettings().then((res) => {
        if (res.success && res.data) {
          setBackupDir(res.data.backupDir || '');
          setCustomAdbPath(res.data.customAdbPath || '');
          setDerivationProfile(res.data.derivationProfile || 'standard');
        }
      });
    }
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isSaving) return;
    
    setIsSaving(true);
    setSaveStatus(null);

    if (window.electronAPI && window.electronAPI.saveSettings) {
      const res = await window.electronAPI.saveSettings({
        backupDir,
        customAdbPath,
        derivationProfile
      });

      if (res.success) {
        setSaveStatus('success');
      } else {
        setSaveStatus('error');
      }
    } else {
      setSaveStatus('error');
    }

    setIsSaving(false);

    // Clear status notification after 3 seconds
    setTimeout(() => {
      setSaveStatus(null);
    }, 3000);
  };

  return (
    <div style={{
      backgroundColor: '#161b22',
      border: '1px solid #30363d',
      borderRadius: '8px',
      padding: '25px',
      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
      maxWidth: '700px'
    }}>
      <h2 style={{ margin: '0 0 20px 0', color: '#58a6ff', borderBottom: '1px solid #30363d', paddingBottom: '10px' }}>
        System Settings
      </h2>

      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {/* Backup directory path */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontWeight: 'bold', fontSize: '14px' }}>Backup Destination Directory</label>
          <input
            type="text"
            value={backupDir}
            onChange={(e) => setBackupDir(e.target.value)}
            required
            style={{
              padding: '10px',
              backgroundColor: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#c9d1d9',
              fontSize: '14px',
              outline: 'none'
            }}
          />
          <span style={{ fontSize: '12px', color: '#8b949e' }}>
            Absolute path where exported backup archives, reports, and manifests will be written.
          </span>
        </div>

        {/* Custom ADB Path override */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontWeight: 'bold', fontSize: '14px' }}>Custom ADB Binary Path (Optional)</label>
          <input
            type="text"
            value={customAdbPath}
            onChange={(e) => setCustomAdbPath(e.target.value)}
            placeholder="e.g. C:\platform-tools\adb.exe"
            style={{
              padding: '10px',
              backgroundColor: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#c9d1d9',
              fontSize: '14px',
              outline: 'none'
            }}
          />
          <span style={{ fontSize: '12px', color: '#8b949e' }}>
            Leave blank to use the system default or auto-resolved SDK installation paths.
          </span>
        </div>

        {/* Key Derivation Rounds */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <label style={{ fontWeight: 'bold', fontSize: '14px' }}>Cryptographic Derivation Complexity</label>
          <select
            value={derivationProfile}
            onChange={(e) => setDerivationProfile(e.target.value as any)}
            style={{
              padding: '10px',
              backgroundColor: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#c9d1d9',
              fontSize: '14px',
              outline: 'none',
              cursor: 'pointer'
            }}
          >
            <option value="standard">Standard (Standard speed & security - 4 rounds)</option>
            <option value="enhanced">Enhanced (Recommended for multi-core processors - 8 rounds)</option>
            <option value="paranoid">Paranoid (High security, slower key derivation - 16 rounds)</option>
          </select>
          <span style={{ fontSize: '12px', color: '#8b949e' }}>
            Controls Argon2id parameters when deriving backup archive master keys. Higher profiles require more CPU/RAM.
          </span>
        </div>

        {/* Status notification */}
        {saveStatus === 'success' && (
          <div style={{
            backgroundColor: '#1b4721',
            border: '1px solid #2ea043',
            color: '#c9d1d9',
            padding: '10px',
            borderRadius: '6px',
            fontSize: '14px'
          }}>
            [+] System settings saved successfully! ADB connection has been re-indexed.
          </div>
        )}

        {saveStatus === 'error' && (
          <div style={{
            backgroundColor: '#441d18',
            border: '1px solid #f85149',
            color: '#c9d1d9',
            padding: '10px',
            borderRadius: '6px',
            fontSize: '14px'
          }}>
            [-] Failed to save system configuration settings. Check process logs.
          </div>
        )}

        {/* Save button */}
        <button
          type="submit"
          disabled={isSaving}
          style={{
            padding: '10px 20px',
            backgroundColor: isSaving ? '#21262d' : '#238636',
            border: '1px solid #30363d',
            color: isSaving ? '#8b949e' : '#fff',
            cursor: isSaving ? 'not-allowed' : 'pointer',
            borderRadius: '6px',
            fontWeight: 'bold',
            alignSelf: 'flex-start',
            transition: 'background-color 0.2s',
            fontSize: '14px',
            outline: 'none'
          }}
          onMouseOver={(e) => {
            if (!isSaving) e.currentTarget.style.backgroundColor = '#2ea043';
          }}
          onMouseOut={(e) => {
            if (!isSaving) e.currentTarget.style.backgroundColor = '#238636';
          }}
        >
          {isSaving ? 'Saving...' : 'Save Settings'}
        </button>
      </form>
    </div>
  );
}
export default SettingsPanel;
