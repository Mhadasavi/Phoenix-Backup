import React, { useState } from 'react';
import { KeyDerivationRequest, IpcResponse, KeyDerivationResponse } from '@phoenix/shared/types';

/**
 * Sprint 1 - Master Key Derivation Panel.
 * Uses worker processes in the main thread to securely generate cryptographic keys.
 */
interface KeyDerivationPanelProps {
  onKeyDerived?: (keyHex: string | null) => void;
}

export function KeyDerivationPanel({ onKeyDerived }: KeyDerivationPanelProps) {
  const [passphrase, setPassphrase] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<KeyDerivationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDeriveKey = async () => {
    if (!passphrase) return;

    setIsProcessing(true);
    setError(null);
    setResult(null);

    try {
      const request: KeyDerivationRequest = { passphrase };
      // Invoke IPC call to derive master key
      const response: IpcResponse<KeyDerivationResponse> = await window.electronAPI.derivePassphraseKey(request);

      if (response.success && response.data) {
        setResult(response.data);
        if (onKeyDerived && response.data.keyHex) {
          onKeyDerived(response.data.keyHex);
        }
      } else {
        setError(response.error || 'Failed to derive master key.');
        if (onKeyDerived) onKeyDerived(null);
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred.');
      if (onKeyDerived) onKeyDerived(null);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div style={{
      backgroundColor: '#161b22',
      border: '1px solid #30363d',
      borderRadius: '8px',
      padding: '20px',
      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
    }}>
      <h3 style={{ margin: '0 0 15px 0' }}>Backup Encryption Configuration</h3>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '5px', fontSize: '14px' }}>
            Set Backup Master Passphrase
          </label>
          <input 
            type="password" 
            value={passphrase} 
            onChange={(e) => setPassphrase(e.target.value)}
            placeholder="Enter a strong passphrase"
            disabled={isProcessing}
            style={{
              width: '100%',
              padding: '8px',
              backgroundColor: '#0d1117',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#fff',
              boxSizing: 'border-box'
            }}
          />
        </div>

        <button 
          onClick={handleDeriveKey}
          disabled={isProcessing || !passphrase}
          style={{
            padding: '10px',
            backgroundColor: isProcessing || !passphrase ? '#21262d' : '#238636',
            color: isProcessing || !passphrase ? '#8b949e' : '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: isProcessing || !passphrase ? 'default' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {isProcessing ? 'Generating Key via Argon2id...' : 'Initialize Secure Master Key'}
        </button>

        {error && (
          <div style={{ color: '#f85149', fontSize: '14px', marginTop: '10px' }}>
            {error}
          </div>
        )}

        {result && result.success && (
          <div style={{
            backgroundColor: '#0f141c',
            border: '1px solid #1f6feb',
            padding: '12px',
            borderRadius: '6px',
            fontSize: '13px',
            marginTop: '10px'
          }}>
            <div style={{ color: '#58a6ff', fontWeight: 'bold', marginBottom: '5px' }}>
              ✓ Master Key Initialized
            </div>
            <div style={{ wordBreak: 'break-all', color: '#8b949e' }}>
              <strong>Key Hash:</strong> {result.keyHex}
            </div>
            <div style={{ wordBreak: 'break-all', color: '#8b949e', marginTop: '5px' }}>
              <strong>Salt:</strong> {result.saltHex}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
export default KeyDerivationPanel;
