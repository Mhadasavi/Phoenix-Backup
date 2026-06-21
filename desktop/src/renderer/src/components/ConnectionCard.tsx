import React, { useEffect, useState } from 'react';
import { AdbConnectionUpdate, DeviceStatus } from '@phoenix/shared/types';

/**
 * Sprint 1 - USB Connection Diagnostic Card.
 * Receives IPC updates from the main discovery thread and guides the user.
 */
export function ConnectionCard() {
  const [status, setStatus] = useState<DeviceStatus>('DISCONNECTED');
  const [deviceInfo, setDeviceInfo] = useState<any>(null);
  const [isRetrying, setIsRetrying] = useState(false);

  useEffect(() => {
    // Query initial connection status on component mount (e.g. when switching tabs back to dashboard)
    if (window.electronAPI && window.electronAPI.getCurrentDeviceState) {
      window.electronAPI.getCurrentDeviceState().then((res) => {
        if (res.success && res.data) {
          setStatus(res.data.status);
          setDeviceInfo(res.data.device);
        }
      });
    }

    // Register event listener for device connection changes pushed from Electron main
    if (window.electronAPI && window.electronAPI.onDeviceStateChange) {
      window.electronAPI.onDeviceStateChange((event, data: AdbConnectionUpdate) => {
        setStatus(data.status);
        setDeviceInfo(data.device);
      });
    }
  }, []);

  const handleRetry = async () => {
    if (isRetrying) return;
    setIsRetrying(true);
    if (window.electronAPI && window.electronAPI.retryDeviceConnection) {
      await window.electronAPI.retryDeviceConnection();
    }
    // Retain scanning state briefly for micro-animation feedback
    setTimeout(() => {
      setIsRetrying(false);
    }, 1000);
  };

  return (
    <div style={{
      backgroundColor: '#161b22',
      border: '1px solid #30363d',
      borderRadius: '8px',
      padding: '20px',
      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
    }}>
      <h3 style={{ margin: '0 0 15px 0' }}>Device Connection Status</h3>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '15px' }}>
        <div style={{
          width: '12px',
          height: '12px',
          borderRadius: '50%',
          backgroundColor: status === 'CONNECTED' ? '#238636' : status === 'UNAUTHORIZED' ? '#d29922' : '#f85149'
        }} />
        <span style={{ fontWeight: 'bold' }}>{status}</span>
      </div>

      {status === 'CONNECTED' && deviceInfo && (
        <div style={{ fontSize: '14px', color: '#8b949e' }}>
          <div><strong>Manufacturer:</strong> {deviceInfo.manufacturer}</div>
          <div><strong>Model:</strong> {deviceInfo.model}</div>
          <div><strong>Android Version:</strong> {deviceInfo.androidVersion}</div>
          <div><strong>API Level:</strong> {deviceInfo.apiLevel}</div>
        </div>
      )}

      {status === 'UNAUTHORIZED' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <div style={{
            backgroundColor: '#382305',
            border: '1px solid #d29922',
            padding: '10px',
            borderRadius: '6px',
            fontSize: '14px',
            color: '#f0e6d2'
          }}>
            <strong>Action Required:</strong> Please check your Android screen and authorize USB debugging to proceed.
          </div>
          <button
            onClick={handleRetry}
            disabled={isRetrying}
            style={{
              padding: '8px 16px',
              backgroundColor: isRetrying ? '#21262d' : '#1f6feb',
              border: '1px solid #30363d',
              color: isRetrying ? '#8b949e' : '#fff',
              cursor: isRetrying ? 'not-allowed' : 'pointer',
              borderRadius: '6px',
              fontWeight: 'bold',
              alignSelf: 'flex-start',
              transition: 'background-color 0.2s',
              fontSize: '13px',
              outline: 'none'
            }}
            onMouseOver={(e) => {
              if (!isRetrying) e.currentTarget.style.backgroundColor = '#388bfd';
            }}
            onMouseOut={(e) => {
              if (!isRetrying) e.currentTarget.style.backgroundColor = '#1f6feb';
            }}
          >
            {isRetrying ? 'Scanning...' : 'Retry Scan'}
          </button>
        </div>
      )}

      {status === 'DISCONNECTED' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          <div style={{ fontSize: '14px', color: '#8b949e' }}>
            Please connect your Android device using a compatible USB debugging cable.
          </div>
          <button
            onClick={handleRetry}
            disabled={isRetrying}
            style={{
              padding: '8px 16px',
              backgroundColor: isRetrying ? '#21262d' : '#238636',
              border: '1px solid #30363d',
              color: isRetrying ? '#8b949e' : '#fff',
              cursor: isRetrying ? 'not-allowed' : 'pointer',
              borderRadius: '6px',
              fontWeight: 'bold',
              alignSelf: 'flex-start',
              transition: 'background-color 0.2s',
              fontSize: '13px',
              outline: 'none'
            }}
            onMouseOver={(e) => {
              if (!isRetrying) e.currentTarget.style.backgroundColor = '#2ea043';
            }}
            onMouseOut={(e) => {
              if (!isRetrying) e.currentTarget.style.backgroundColor = '#238636';
            }}
          >
            {isRetrying ? 'Scanning...' : 'Retry Scan'}
          </button>
        </div>
      )}
    </div>
  );
}
export default ConnectionCard;
