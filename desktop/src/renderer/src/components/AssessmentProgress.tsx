import React, { useEffect, useState, useRef } from 'react';

interface AssessmentProgressProps {
  onCancel: () => void;
  deviceInfo: {
    manufacturer: string;
    model: string;
    androidVersion: string;
    apiLevel: number;
  } | null;
}

export function AssessmentProgress({ onCancel, deviceInfo }: AssessmentProgressProps) {
  const [progress, setProgress] = useState(0);
  const [activeMilestone, setActiveMilestone] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const consoleRef = useRef<HTMLDivElement>(null);

  const milestones = [
    'Initialize Database Schema Connections',
    'Crawl App Inventory Packages',
    'Classifying Packages & Extracting Permissions',
    'Evaluating Storage Blocks (DCIM, Downloads)',
    'Compiling Readiness Checklist & Sorter'
  ];

  useEffect(() => {
    // Dynamic progress bar increments to simulate active diagnostic scan phases
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 98) {
          clearInterval(interval);
          return 98;
        }
        const step = Math.floor(Math.random() * 3) + 1;
        const nextProgress = Math.min(prev + step, 98);
        
        // Map progress intervals to milestones
        if (nextProgress < 20) setActiveMilestone(0);
        else if (nextProgress < 45) setActiveMilestone(1);
        else if (nextProgress < 70) setActiveMilestone(2);
        else if (nextProgress < 90) setActiveMilestone(3);
        else setActiveMilestone(4);

        return nextProgress;
      });
    }, 100);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    // Subscribe to real-time console log streams
    if (window.electronAPI && window.electronAPI.onAssessmentLog) {
      window.electronAPI.onAssessmentLog((event, log: string) => {
        setLogs(prev => [...prev, log]);
      });
    }
  }, []);

  useEffect(() => {
    // Auto-scroll to the bottom of the console container when new logs arrive
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div style={{
      backgroundColor: '#161b22',
      border: '1px solid #30363d',
      borderRadius: '8px',
      padding: '25px',
      boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
      display: 'flex',
      flexDirection: 'column',
      gap: '20px'
    }}>
      <div>
        <h3 style={{ margin: '0 0 5px 0', color: '#58a6ff' }}>
          Auditing Target Device: {deviceInfo ? `${deviceInfo.manufacturer} ${deviceInfo.model}` : 'Android Device'}
        </h3>
        <p style={{ margin: 0, fontSize: '13px', color: '#8b949e' }}>
          API Level {deviceInfo?.apiLevel || 'Unknown'} • Android {deviceInfo?.androidVersion || 'Unknown'}
        </p>
      </div>

      {/* Progress Bar Container */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '14px', fontWeight: 'bold' }}>
          <span>Diagnostics Progress</span>
          <span style={{ color: '#58a6ff' }}>{progress}%</span>
        </div>
        <div style={{
          width: '100%',
          height: '10px',
          backgroundColor: '#0d1117',
          borderRadius: '5px',
          overflow: 'hidden',
          border: '1px solid #30363d'
        }}>
          <div style={{
            width: `${progress}%`,
            height: '100%',
            backgroundColor: '#1f6feb',
            borderRadius: '5px',
            transition: 'width 0.2s ease-out',
            boxShadow: '0 0 8px rgba(31, 111, 235, 0.6)'
          }} />
        </div>
      </div>

      {/* Milestones Panel */}
      <div>
        <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#c9d1d9' }}>Assessment Milestones</h4>
        <div style={{
          backgroundColor: '#0d1117',
          border: '1px solid #30363d',
          borderRadius: '6px',
          padding: '15px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          {milestones.map((milestone, idx) => {
            const isCompleted = idx < activeMilestone;
            const isActive = idx === activeMilestone;
            
            return (
              <div key={idx} style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: '13.5px',
                color: isCompleted ? '#8b949e' : isActive ? '#c9d1d9' : '#484f58'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {isCompleted ? (
                    <span style={{ color: '#238636', fontWeight: 'bold' }}>[✔]</span>
                  ) : isActive ? (
                    <span style={{ color: '#d29922', fontWeight: 'bold', display: 'inline-block', animation: 'spin 1s linear infinite' }}>[/]</span>
                  ) : (
                    <span style={{ color: '#484f58' }}>[ ]</span>
                  )}
                  <span style={{ textDecoration: isCompleted ? 'line-through' : 'none' }}>
                    {milestone}
                  </span>
                </div>
                <span style={{
                  fontWeight: 'bold',
                  fontSize: '12px',
                  color: isCompleted ? '#238636' : isActive ? '#d29922' : '#484f58'
                }}>
                  {isCompleted ? 'OK' : isActive ? 'RUNNING' : 'PENDING'}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Real-time Console Log Console */}
      <div>
        <h4 style={{ margin: '0 0 12px 0', fontSize: '14px', color: '#c9d1d9' }}>Real-time Audit Console Logs</h4>
        <div 
          ref={consoleRef}
          style={{
            backgroundColor: '#0d1117',
            border: '1px solid #30363d',
            borderRadius: '6px',
            padding: '12px',
            fontFamily: 'Consolas, Monaco, monospace',
            fontSize: '11px',
            color: '#8b949e',
            height: '140px',
            overflowY: 'auto',
            whiteSpace: 'pre-wrap',
            lineHeight: '1.4',
            boxShadow: 'inset 0 0 8px rgba(0, 0, 0, 0.5)'
          }}
        >
          {logs.length === 0 ? (
            <span style={{ fontStyle: 'italic', color: '#484f58' }}>Establishing ADB terminal listener...</span>
          ) : (
            logs.join('')
          )}
        </div>
      </div>

      <button
        onClick={onCancel}
        style={{
          alignSelf: 'flex-start',
          padding: '8px 16px',
          backgroundColor: '#21262d',
          border: '1px solid #30363d',
          color: '#f85149',
          borderRadius: '6px',
          cursor: 'pointer',
          fontWeight: 'bold',
          transition: 'background-color 0.2s'
        }}
        onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#30363d'}
        onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#21262d'}
      >
        Cancel Scan
      </button>

      {/* Inline styles for custom spinning keyframes animation */}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default AssessmentProgress;
