import React, { useState, useEffect } from 'react';
import { ConnectionCard } from './components/ConnectionCard';
import { KeyDerivationPanel } from './components/KeyDerivationPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { AssessmentProgress } from './components/AssessmentProgress';
import { AssessmentResults } from './components/AssessmentResults';
import { BackupArtifactsDashboard } from './components/BackupArtifactsDashboard';
import { AdbConnectionUpdate, DeviceStatus } from '@phoenix/shared/types';

/**
 * Phoenix Backup - Main Application View Layout (Sprint 2.5 UI Integration)
 */
export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'settings'>('dashboard');
  
  // Dashboard scan states
  const [scanState, setScanState] = useState<'initial' | 'scanning' | 'results'>('initial');
  const [resultData, setResultData] = useState<any | null>(null);
  const [overrides, setOverrides] = useState<string[]>([]);

  // Connection and ADB state hooks
  const [deviceStatus, setDeviceStatus] = useState<DeviceStatus>('DISCONNECTED');
  const [deviceInfo, setDeviceInfo] = useState<any>(null);
  const [adbError, setAdbError] = useState<string | null>(null);

  // Authorization/Cryptographic key state
  const [masterKeyHex, setMasterKeyHex] = useState<string | null>(null);

  // Backup sync states
  const [backupState, setBackupState] = useState<'initial' | 'backing_up' | 'completed' | 'failed'>('initial');
  const [backupLogs, setBackupLogs] = useState<string>('');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  useEffect(() => {
    // Fetch initial device connection status on load
    if (window.electronAPI && window.electronAPI.getCurrentDeviceState) {
      window.electronAPI.getCurrentDeviceState().then((res) => {
        if (res.success && res.data) {
          setDeviceStatus(res.data.status);
          setDeviceInfo(res.data.device);
          setAdbError(res.data.adbError || null);
        }
      });
    }

    // Subscribe to real-time ADB USB status updates from Electron main process
    if (window.electronAPI && window.electronAPI.onDeviceStateChange) {
      window.electronAPI.onDeviceStateChange((event, data: AdbConnectionUpdate) => {
        setDeviceStatus(data.status);
        setDeviceInfo(data.device);
        setAdbError(data.adbError || null);
      });
    }
  }, []);

  const handleStartAssessment = async (currentOverridesList = overrides) => {
    if (deviceStatus !== 'CONNECTED' || !deviceInfo || !masterKeyHex) return;

    setScanState('scanning');
    try {
      const res = await window.electronAPI.runAssessment(deviceInfo.deviceId, currentOverridesList);
      if (res.success && res.data) {
        setResultData(res.data);
        setActiveJobId(res.data.job_id);
        setScanState('results');
        setBackupState('initial');
      } else {
        alert(res.error || 'Failed to complete pre-flight assessment audit.');
        setScanState('initial');
      }
    } catch (err: any) {
      alert(err.message || 'An unexpected error occurred during the assessment run.');
      setScanState('initial');
    }
  };

  const handleStartBackup = async () => {
    if (deviceStatus !== 'CONNECTED' || !deviceInfo) return;

    setBackupState('backing_up');
    setBackupLogs('Initializing ADB TCP Tunnel forwarding on port 50051...\n');

    // Subscribe to real-time backup logs
    if (window.electronAPI && window.electronAPI.onBackupLog) {
      window.electronAPI.onBackupLog((event, log: string) => {
        setBackupLogs((prev) => prev + log);
      });
    }

    try {
      // Execute the backup using the CLI script via IPC
      const res = await window.electronAPI.runBackup(deviceInfo.deviceId, 'sprint2_integrated_salt');
      if (res.success && res.data) {
        setActiveJobId(res.data.job_id);
        setBackupState('completed');
      } else {
        alert(res.error || 'Backup extraction failed.');
        setBackupState('failed');
      }
    } catch (err: any) {
      alert(err.message || 'An unexpected error occurred during backup.');
      setBackupState('failed');
    }
  };

  const handleOverrideChange = (newOverrides: string[]) => {
    setOverrides(newOverrides);
    handleStartAssessment(newOverrides);
  };

  const handleReset = () => {
    setScanState('initial');
    setResultData(null);
    setOverrides([]);
    setBackupState('initial');
    setActiveJobId(null);
  };

  const isStartAssessmentEnabled = deviceStatus === 'CONNECTED' && masterKeyHex !== null;

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ borderBottom: '1px solid #30363d', paddingBottom: '15px', marginBottom: '25px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, color: '#58a6ff', fontSize: '24px' }}>Phoenix Backup</h1>
          <p style={{ margin: '5px 0 0 0', color: '#8b949e', fontSize: '13px' }}>AI-Powered Offline Android Migration Guide</p>
        </div>
        <div style={{ fontSize: '12px', color: '#8b949e', backgroundColor: '#161b22', padding: '6px 12px', borderRadius: '15px', border: '1px solid #30363d' }}>
          Sprint 2.5 Stable Release
        </div>
      </header>

      {/* Warning banner for missing ADB/paths */}
      {activeTab === 'dashboard' && adbError && (
        <div style={{
          backgroundColor: '#382305',
          border: '1px solid #d29922',
          padding: '12px 18px',
          borderRadius: '8px',
          color: '#f0e6d2',
          marginBottom: '20px',
          fontSize: '13.5px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <span style={{ fontSize: '18px' }}>⚠️</span>
          <div>
            <strong>ADB Service Issue:</strong> {adbError}. Check your custom Android SDK Platform Tools or setup paths in the settings menu.
          </div>
        </div>
      )}

      <div style={{ display: 'flex', gap: '25px', flex: 1 }}>
        {/* Navigation Sidebar */}
        <aside style={{ width: '220px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <button 
            onClick={() => setActiveTab('dashboard')} 
            style={{
              padding: '12px 15px',
              textAlign: 'left',
              backgroundColor: activeTab === 'dashboard' ? '#1f6feb' : 'transparent',
              border: 'none',
              color: '#fff',
              cursor: 'pointer',
              borderRadius: '6px',
              fontWeight: 'bold',
              transition: 'background-color 0.2s',
              outline: 'none'
            }}
            onMouseOver={(e) => { if (activeTab !== 'dashboard') e.currentTarget.style.backgroundColor = '#21262d'; }}
            onMouseOut={(e) => { if (activeTab !== 'dashboard') e.currentTarget.style.backgroundColor = 'transparent'; }}
          >
            Dashboard
          </button>
          
          <button 
            onClick={() => setActiveTab('settings')}
            style={{
              padding: '12px 15px',
              textAlign: 'left',
              backgroundColor: activeTab === 'settings' ? '#1f6feb' : 'transparent',
              border: 'none',
              color: '#fff',
              cursor: 'pointer',
              borderRadius: '6px',
              fontWeight: 'bold',
              transition: 'background-color 0.2s',
              outline: 'none'
            }}
            onMouseOver={(e) => { if (activeTab !== 'settings') e.currentTarget.style.backgroundColor = '#21262d'; }}
            onMouseOut={(e) => { if (activeTab !== 'settings') e.currentTarget.style.backgroundColor = 'transparent'; }}
          >
            Settings
          </button>
        </aside>

        {/* Content Viewport */}
        <main style={{ flex: 1, minWidth: 0 }}>
          {activeTab === 'settings' ? (
            <SettingsPanel />
          ) : (
            /* Dashboard state machine */
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              {scanState === 'initial' && (
                <>
                  <ConnectionCard />
                  <KeyDerivationPanel onKeyDerived={(key) => setMasterKeyHex(key)} />
                  
                  {/* Start scan execution action */}
                  <button
                    onClick={() => handleStartAssessment()}
                    disabled={!isStartAssessmentEnabled}
                    style={{
                      padding: '14px',
                      backgroundColor: isStartAssessmentEnabled ? '#238636' : '#21262d',
                      color: isStartAssessmentEnabled ? '#fff' : '#8b949e',
                      border: 'none',
                      borderRadius: '8px',
                      cursor: isStartAssessmentEnabled ? 'pointer' : 'not-allowed',
                      fontWeight: 'bold',
                      fontSize: '15px',
                      transition: 'background-color 0.2s',
                      textAlign: 'center',
                      boxShadow: isStartAssessmentEnabled ? '0 4px 10px rgba(35, 134, 54, 0.4)' : 'none'
                    }}
                    onMouseOver={(e) => { if (isStartAssessmentEnabled) e.currentTarget.style.backgroundColor = '#2ea043'; }}
                    onMouseOut={(e) => { if (isStartAssessmentEnabled) e.currentTarget.style.backgroundColor = '#238636'; }}
                  >
                    {!masterKeyHex 
                      ? 'Initialize Master Key to Enable Assessment' 
                      : deviceStatus !== 'CONNECTED' 
                        ? 'Connect Android Device to Enable Assessment'
                        : 'START FLIGHT ASSESSMENT'}
                  </button>
                </>
              )}

              {scanState === 'scanning' && (
                <AssessmentProgress
                  deviceInfo={deviceInfo}
                  onCancel={handleReset}
                />
              )}

              {scanState === 'results' && resultData && (
                <>
                  <AssessmentResults
                    resultData={resultData}
                    deviceInfo={deviceInfo}
                    onReset={handleReset}
                    onOverrideChange={handleOverrideChange}
                    currentOverrides={overrides}
                  />
                  
                  {/* Backup Controller Section */}
                  <div style={{
                    backgroundColor: '#161b22',
                    border: '1px solid #30363d',
                    borderRadius: '8px',
                    padding: '20px',
                    marginTop: '20px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '15px'
                  }}>
                    <style>{`
                      @keyframes spin {
                        to { transform: rotate(360deg); }
                      }
                    `}</style>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <h3 style={{ color: '#c9d1d9', fontSize: '16px', fontWeight: 'bold', margin: 0 }}>
                          Secure Data Extraction Client
                        </h3>
                        <p style={{ color: '#8b949e', fontSize: '13px', margin: '5px 0 0 0' }}>
                          Establish secure TCP tunnel and execute signed HMAC data extraction from the companion app.
                        </p>
                      </div>
                      <button
                        onClick={handleStartBackup}
                        disabled={deviceStatus !== 'CONNECTED' || backupState === 'backing_up'}
                        style={{
                          padding: '10px 20px',
                          backgroundColor: deviceStatus === 'CONNECTED' && backupState !== 'backing_up' ? '#238636' : '#21262d',
                          color: deviceStatus === 'CONNECTED' && backupState !== 'backing_up' ? '#fff' : '#8b949e',
                          border: 'none',
                          borderRadius: '6px',
                          cursor: deviceStatus === 'CONNECTED' && backupState !== 'backing_up' ? 'pointer' : 'not-allowed',
                          fontWeight: 'bold',
                          fontSize: '13px',
                          transition: 'background-color 0.2s',
                          boxShadow: deviceStatus === 'CONNECTED' && backupState !== 'backing_up' ? '0 4px 10px rgba(35, 134, 54, 0.3)' : 'none'
                        }}
                        onMouseOver={(e) => { if (deviceStatus === 'CONNECTED' && backupState !== 'backing_up') e.currentTarget.style.backgroundColor = '#2ea043'; }}
                        onMouseOut={(e) => { if (deviceStatus === 'CONNECTED' && backupState !== 'backing_up') e.currentTarget.style.backgroundColor = '#238636'; }}
                      >
                        {backupState === 'backing_up' ? 'Extracting...' : 'Run Secure Data Extraction'}
                      </button>
                    </div>

                    {/* Extraction State & Logs */}
                    {backupState !== 'initial' && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        {backupState === 'backing_up' && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#58a6ff', fontSize: '13px' }}>
                            <span className="spinner" style={{
                              display: 'inline-block',
                              width: '12px',
                              height: '12px',
                              border: '2px solid #58a6ff',
                              borderTopColor: 'transparent',
                              borderRadius: '50%',
                              animation: 'spin 1s linear infinite'
                            }} />
                            <span>Backup extraction in progress. Do not disconnect the device...</span>
                          </div>
                        )}

                        {backupState === 'completed' && (
                          <div style={{
                            backgroundColor: '#1b4721',
                            border: '1px solid #2ea043',
                            borderRadius: '6px',
                            padding: '10px 15px',
                            color: '#c9d1d9',
                            fontSize: '13px'
                          }}>
                            <strong>[+] Success:</strong> Data extraction completed successfully! SQLite records populated.
                          </div>
                        )}

                        {backupState === 'failed' && (
                          <div style={{
                            backgroundColor: '#441d18',
                            border: '1px solid #f85149',
                            borderRadius: '6px',
                            padding: '10px 15px',
                            color: '#c9d1d9',
                            fontSize: '13px'
                          }}>
                            <strong>[-] Error:</strong> Data extraction failed. Check connection status and server log detail below.
                          </div>
                        )}

                        <div style={{ position: 'relative' }}>
                          <div style={{
                            fontSize: '11px',
                            color: '#8b949e',
                            position: 'absolute',
                            top: '8px',
                            right: '12px',
                            textTransform: 'uppercase',
                            fontWeight: 'bold',
                            letterSpacing: '0.05em'
                          }}>
                            Live Console Logs
                          </div>
                          <textarea
                            readOnly
                            value={backupLogs}
                            ref={(el) => {
                              if (el) el.scrollTop = el.scrollHeight;
                            }}
                            style={{
                              width: '100%',
                              height: '180px',
                              backgroundColor: '#0d1117',
                              border: '1px solid #30363d',
                              borderRadius: '6px',
                              padding: '12px',
                              color: '#c9d1d9',
                              fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                              fontSize: '12px',
                              lineHeight: '1.5',
                              resize: 'none',
                              outline: 'none',
                              boxSizing: 'border-box'
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </div>

                  <BackupArtifactsDashboard key={activeJobId + '_' + backupState} jobId={activeJobId} />
                </>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

import { createRoot } from 'react-dom/client';

const container = document.getElementById('root');
if (container) {
  const root = createRoot(container);
  root.render(<App />);
}

export default App;
