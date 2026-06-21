import React, { useState, useEffect } from 'react';
import { IpcResponse } from '@phoenix/shared/types';

interface ExtractionLog {
  data_type: 'CONTACTS' | 'SMS' | 'CALL_LOGS' | 'SYSTEM_INFO';
  status: 'SUCCESS' | 'FAILED' | 'PERMISSION_DENIED';
  records_extracted: number;
  timestamp: string;
}

interface BackupArtifactsDashboardProps {
  jobId: string | null;
}

export function BackupArtifactsDashboard({ jobId }: BackupArtifactsDashboardProps) {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<Record<string, ExtractionLog>>({});

  const fetchLogs = async (targetJobId: string) => {
    setLoading(true);
    setError(null);
    try {
      const response: IpcResponse<ExtractionLog[]> = await window.electronAPI.getExtractionLogs(targetJobId);
      if (response.success && response.data) {
        const mappedLogs: Record<string, ExtractionLog> = {};
        response.data.forEach(log => {
          mappedLogs[log.data_type] = log;
        });
        setLogs(mappedLogs);
      } else {
        setError(response.error || 'Failed to retrieve database extraction logs.');
      }
    } catch (err: any) {
      setError(err.message || 'An unexpected error occurred while querying database.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (jobId) {
      fetchLogs(jobId);
    } else {
      setLogs({});
      setError(null);
      setLoading(false);
    }
  }, [jobId]);

  // Status badge style resolver
  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'SUCCESS':
        return { color: '#3fb950', backgroundColor: '#3fb95015', border: '1px solid #238636' };
      case 'PERMISSION_DENIED':
        return { color: '#d29922', backgroundColor: '#d2992215', border: '1px solid #9e6a00' };
      case 'FAILED':
      default:
        return { color: '#f85149', backgroundColor: '#f8514915', border: '1px solid #da3633' };
    }
  };

  // Human-readable timestamps formatting
  const formatTimestamp = (isoString: string) => {
    try {
      const date = new Date(isoString.replace(' ', 'T') + 'Z'); // Normalize sqlite timestamp to UTC ISO
      return date.toLocaleString();
    } catch (e) {
      return isoString;
    }
  };

  // Render Card
  const renderCard = (
    title: string,
    key: 'CONTACTS' | 'SMS' | 'CALL_LOGS',
    iconPath: string
  ) => {
    const log = logs[key];

    if (!log) {
      return (
        <div style={cardStyle}>
          <div style={cardHeaderStyle}>
            <div style={iconContainerStyle}>{title[0]}</div>
            <span style={{ fontWeight: 'bold', fontSize: '14px', color: '#c9d1d9' }}>{title}</span>
          </div>
          <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#8b949e', margin: '15px 0' }}>
            Not Extracted
          </div>
          <div style={{ fontSize: '11px', color: '#8b949e' }}>No extraction attempt run for this job.</div>
        </div>
      );
    }

    const statusStyle = getStatusStyle(log.status);

    return (
      <div style={cardStyle}>
        <div style={cardHeaderStyle}>
          <div style={iconContainerStyle}>{title[0]}</div>
          <span style={{ fontWeight: 'bold', fontSize: '14px', color: '#c9d1d9' }}>{title}</span>
          <span style={{
            fontSize: '10px',
            fontWeight: 'bold',
            padding: '2px 6px',
            borderRadius: '4px',
            marginLeft: 'auto',
            ...statusStyle
          }}>
            {log.status}
          </span>
        </div>
        <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#58a6ff', margin: '15px 0 10px 0' }}>
          {log.status === 'SUCCESS' ? log.records_extracted.toLocaleString() : '—'}
          <span style={{ fontSize: '14px', fontWeight: 'normal', color: '#8b949e', marginLeft: '5px' }}>
            records
          </span>
        </div>
        <div style={{ fontSize: '11px', color: '#8b949e', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <div><strong>Type:</strong> {log.data_type}</div>
          <div><strong>Sync time:</strong> {formatTimestamp(log.timestamp)}</div>
        </div>
      </div>
    );
  };

  // Render Skeleton Screen (pulse loading states)
  const renderSkeletonCard = () => (
    <div style={{ ...cardStyle, animation: 'pulse 1.5s infinite ease-in-out' }}>
      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
        <div style={{ width: '28px', height: '28px', borderRadius: '4px', backgroundColor: '#21262d' }} />
        <div style={{ width: '80px', height: '14px', borderRadius: '4px', backgroundColor: '#21262d' }} />
      </div>
      <div style={{ width: '120px', height: '28px', borderRadius: '4px', backgroundColor: '#21262d', margin: '20px 0 15px 0' }} />
      <div style={{ width: '150px', height: '12px', borderRadius: '4px', backgroundColor: '#21262d' }} />
    </div>
  );

  if (!jobId) {
    return (
      <div style={wrapperStyle}>
        <h3 style={titleStyle}>Backup Extraction Vault</h3>
        <div style={{
          backgroundColor: '#161b22',
          border: '1px dashed #30363d',
          borderRadius: '8px',
          padding: '30px',
          textAlign: 'center',
          color: '#8b949e',
          fontSize: '13px'
        }}>
          No active backup jobs logged. Connect a device and run a recovery scan to verify extracted data.
        </div>
      </div>
    );
  }

  return (
    <div style={wrapperStyle}>
      <style>{`
        @keyframes pulse {
          0% { opacity: 0.6; }
          50% { opacity: 0.3; }
          100% { opacity: 0.6; }
        }
      `}</style>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <h3 style={titleStyle}>Backup Extraction Vault</h3>
        <button
          onClick={() => fetchLogs(jobId)}
          disabled={loading}
          style={refreshButtonStyle}
          onMouseOver={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#30363d'; }}
          onMouseOut={(e) => { if (!loading) e.currentTarget.style.backgroundColor = '#21262d'; }}
        >
          {loading ? 'Refreshing...' : 'Refresh Vault'}
        </button>
      </div>

      {error && (
        <div style={errorContainerStyle}>
          <div style={{ fontWeight: 'bold', fontSize: '13px', color: '#ff7b72' }}>Extraction Error Detected</div>
          <div style={{ fontSize: '12px', color: '#8b949e', margin: '4px 0 10px 0' }}>{error}</div>
          <button onClick={() => fetchLogs(jobId)} style={retryButtonStyle}>
            Retry Fetch
          </button>
        </div>
      )}

      {!error && (
        <div style={gridStyle}>
          {loading ? (
            <>
              {renderSkeletonCard()}
              {renderSkeletonCard()}
              {renderSkeletonCard()}
            </>
          ) : (
            <>
              {renderCard('Contacts', 'CONTACTS', 'contacts')}
              {renderCard('SMS Messages', 'SMS', 'sms')}
              {renderCard('Call History', 'CALL_LOGS', 'call_logs')}
            </>
          )}
        </div>
      )}
    </div>
  );
}

// Styling Declarations
const wrapperStyle: React.CSSProperties = {
  backgroundColor: '#0d1117',
  border: '1px solid #30363d',
  borderRadius: '8px',
  padding: '20px',
  marginTop: '20px'
};

const titleStyle: React.CSSProperties = {
  color: '#c9d1d9',
  fontSize: '15px',
  fontWeight: 'bold',
  margin: 0
};

const gridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: '15px',
  marginTop: '10px'
};

const cardStyle: React.CSSProperties = {
  backgroundColor: '#161b22',
  border: '1px solid #30363d',
  borderRadius: '8px',
  padding: '16px',
  display: 'flex',
  flexDirection: 'column',
  transition: 'transform 0.2s ease, border-color 0.2s ease',
  boxShadow: '0 4px 6px rgba(0, 0, 0, 0.15)'
};

const cardHeaderStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: '10px'
};

const iconContainerStyle: React.CSSProperties = {
  width: '28px',
  height: '28px',
  borderRadius: '4px',
  backgroundColor: '#21262d',
  border: '1px solid #30363d',
  color: '#58a6ff',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 'bold',
  fontSize: '12px'
};

const refreshButtonStyle: React.CSSProperties = {
  padding: '6px 12px',
  backgroundColor: '#21262d',
  border: '1px solid #30363d',
  borderRadius: '6px',
  color: '#c9d1d9',
  fontSize: '12px',
  fontWeight: 'bold',
  cursor: 'pointer',
  transition: 'background-color 0.15s ease'
};

const errorContainerStyle: React.CSSProperties = {
  backgroundColor: '#da363308',
  border: '1px solid #f8514930',
  borderRadius: '8px',
  padding: '16px',
  marginTop: '10px'
};

const retryButtonStyle: React.CSSProperties = {
  padding: '6px 12px',
  backgroundColor: '#da363315',
  border: '1px solid #f85149',
  borderRadius: '6px',
  color: '#ff7b72',
  fontSize: '11px',
  fontWeight: 'bold',
  cursor: 'pointer'
};

export default BackupArtifactsDashboard;
