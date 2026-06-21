import React, { useState, useEffect } from 'react';
import { IpcResponse } from '@phoenix/shared/types';

interface Finding {
  package_name: string;
  app_name: string;
  category: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'INFO';
  reasoning: string;
  remediation: string;
  resolved: boolean;
}

interface RecoveryAction {
  action_id: string;
  title: string;
  description: string;
  category: string;
  priority: number;
  status: string;
  is_blocked: boolean;
  blockers: string[];
}

interface AssessmentResultsProps {
  resultData: {
    job_id: string;
    readiness_score: number;
    readiness_state: string;
    analysis: {
      readiness_score: number;
      readiness_state: string;
      verdicts: {
        contacts_ready: boolean;
        sms_ready: boolean;
        call_logs_ready: boolean;
      };
      overall_assessment: string;
      findings: Finding[];
      recovery_sequence: RecoveryAction[];
    };
  };
  deviceInfo: {
    manufacturer: string;
    model: string;
    androidVersion: string;
    apiLevel: number;
  } | null;
  onReset: () => void;
  onOverrideChange: (overrides: string[]) => void;
  currentOverrides: string[];
}

export function AssessmentResults({
  resultData,
  deviceInfo,
  onReset,
  onOverrideChange,
  currentOverrides
}: AssessmentResultsProps) {
  const analysis = resultData.analysis;
  const score = analysis.readiness_score;
  const state = analysis.readiness_state;

  // Local state for checking items in the recommendations list
  const [completedActions, setCompletedActions] = useState<Record<string, boolean>>({});
  const [exportingHtml, setExportingHtml] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [exportStatus, setExportStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Determine colors based on readiness rating thresholds
  const getThemeColor = () => {
    if (score >= 80) return '#238636'; // Green
    if (score >= 50) return '#d29922'; // Yellow
    return '#f85149'; // Red
  };

  const getVerdictLabel = () => {
    if (score >= 80) return 'READY';
    if (score >= 50) return 'PREPARED_WITH_WARNINGS';
    return 'CRITICAL_UNPREPARED';
  };

  const getVerdictDescription = () => {
    if (score >= 80) {
      return 'The device backup configuration is sound. Critical partitions and permissions are verified. Proceed with migration.';
    }
    if (score >= 50) {
      return 'Backup is mostly ready, but warnings exist regarding non-essential applications or settings. Resolve warning items if possible.';
    }
    return 'Wiping device now will result in permanent data loss. Critical multi-factor authentication, secure database applications, or backup configurations are missing. Do not reset device.';
  };

  const handleToggleAction = (actionId: string) => {
    setCompletedActions(prev => ({
      ...prev,
      [actionId]: !prev[actionId]
    }));
  };

  // Toggle app packages to mark as user-resolved/overridden (increases score)
  const handleToggleOverride = (packageName: string) => {
    let nextOverrides: string[];
    if (currentOverrides.includes(packageName)) {
      nextOverrides = currentOverrides.filter(pkg => pkg !== packageName);
    } else {
      nextOverrides = [...currentOverrides, packageName];
    }
    onOverrideChange(nextOverrides);
  };

  const handleExportHtml = async () => {
    if (exportingHtml || exportingPdf) return;
    setExportingHtml(true);
    setExportStatus(null);
    try {
      const res: IpcResponse<string> = await window.electronAPI.exportHtmlReport();
      if (res.success && res.data) {
        setExportStatus({ type: 'success', message: `HTML report exported successfully to: ${res.data}` });
      } else {
        setExportStatus({ type: 'error', message: res.error || 'Failed to export HTML report.' });
      }
    } catch (err: any) {
      setExportStatus({ type: 'error', message: err.message || 'An unexpected error occurred.' });
    } finally {
      setExportingHtml(false);
    }
  };

  const handleExportPdf = async () => {
    if (exportingHtml || exportingPdf) return;
    setExportingPdf(true);
    setExportStatus(null);
    try {
      const res: IpcResponse<string> = await window.electronAPI.exportPdfReport();
      if (res.success && res.data) {
        setExportStatus({ type: 'success', message: `PDF report exported successfully to: ${res.data}` });
      } else {
        setExportStatus({ type: 'error', message: res.error || 'Failed to export PDF report. Target file may be locked.' });
      }
    } catch (err: any) {
      setExportStatus({ type: 'error', message: err.message || 'An unexpected error occurred.' });
    } finally {
      setExportingPdf(false);
    }
  };

  // Setup circle parameters for SVG gauge
  const radius = 60;
  const strokeWidth = 10;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* Device summary header bar */}
      <div style={{
        backgroundColor: '#161b22',
        border: '1px solid #30363d',
        borderRadius: '8px',
        padding: '15px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        <div>
          <span style={{ color: '#8b949e', fontSize: '13px' }}>Audited Device:</span>
          <strong style={{ marginLeft: '6px', color: '#c9d1d9' }}>
            {deviceInfo ? `${deviceInfo.manufacturer} ${deviceInfo.model}` : 'Android Device'}
          </strong>
        </div>
        <div>
          <span style={{ color: '#8b949e', fontSize: '13px' }}>Scan Job ID:</span>
          <span style={{ marginLeft: '6px', fontFamily: 'monospace', color: '#58a6ff', fontSize: '12px' }}>
            {resultData.job_id.substring(0, 8)}...
          </span>
        </div>
      </div>

      {/* Export status banners */}
      {exportStatus && (
        <div style={{
          backgroundColor: exportStatus.type === 'success' ? '#1b4721' : '#441d18',
          border: `1px solid ${exportStatus.type === 'success' ? '#2ea043' : '#f85149'}`,
          padding: '12px',
          borderRadius: '6px',
          fontSize: '14px',
          color: '#c9d1d9'
        }}>
          <strong>{exportStatus.type === 'success' ? '[+]' : '[-]'}</strong> {exportStatus.message}
        </div>
      )}

      {/* Grid: Gauge + Verdict Explanation */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 2fr',
        gap: '20px',
        alignItems: 'stretch'
      }}>
        {/* Gauge Card */}
        <div style={{
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center'
        }}>
          <h4 style={{ margin: '0 0 15px 0', fontSize: '14px', color: '#8b949e' }}>Recovery Readiness</h4>
          
          <div style={{ position: 'relative', width: '140px', height: '140px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="140" height="140" viewBox="0 0 140 140" style={{ transform: 'rotate(-90deg)' }}>
              {/* Background Track */}
              <circle
                cx="70"
                cy="70"
                r={radius}
                fill="transparent"
                stroke="#0d1117"
                strokeWidth={strokeWidth}
              />
              {/* Active Arc */}
              <circle
                cx="70"
                cy="70"
                r={radius}
                fill="transparent"
                stroke={getThemeColor()}
                strokeWidth={strokeWidth}
                strokeDasharray={circumference}
                strokeDashoffset={strokeDashoffset}
                strokeLinecap="round"
                style={{ transition: 'stroke-dashoffset 0.8s ease-in-out' }}
              />
            </svg>
            <div style={{ position: 'absolute', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <span style={{ fontSize: '28px', fontWeight: 'bold', color: '#c9d1d9' }}>{score}</span>
              <span style={{ fontSize: '11px', color: '#8b949e' }}>/ 100</span>
            </div>
          </div>

          <div style={{
            marginTop: '15px',
            padding: '4px 10px',
            borderRadius: '12px',
            backgroundColor: getThemeColor() + '20',
            border: `1px solid ${getThemeColor()}`,
            color: getThemeColor(),
            fontSize: '12px',
            fontWeight: 'bold'
          }}>
            {getVerdictLabel().replace(/_/g, ' ')}
          </div>
        </div>

        {/* Verdict Explanation Card */}
        <div style={{
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '20px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center'
        }}>
          <h3 style={{ margin: '0 0 10px 0', color: getThemeColor() }}>
            Verdict: {getVerdictLabel().replace(/_/g, ' ')}
          </h3>
          <p style={{ margin: '0 0 20px 0', fontSize: '14px', lineHeight: '1.5', color: '#c9d1d9' }}>
            {getVerdictDescription()}
          </p>

          {/* Sync status summaries */}
          <div style={{ display: 'flex', gap: '15px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: analysis.verdicts.contacts_ready ? '#238636' : '#f85149' }} />
              <span style={{ color: '#8b949e' }}>Contacts Sync</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: analysis.verdicts.sms_ready ? '#238636' : '#f85149' }} />
              <span style={{ color: '#8b949e' }}>SMS Database</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: analysis.verdicts.call_logs_ready ? '#238636' : '#f85149' }} />
              <span style={{ color: '#8b949e' }}>Call Logs</span>
            </div>
          </div>
        </div>
      </div>

      {/* Grid: Risks Findings vs Recommendations Checklist */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: '20px',
        alignItems: 'start'
      }}>
        {/* Risks Findings Panel */}
        <div style={{
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '20px',
          maxHeight: '400px',
          overflowY: 'auto'
        }}>
          <h3 style={{ margin: '0 0 15px 0', fontSize: '16px', color: '#58a6ff' }}>Risk Findings</h3>
          
          {analysis.findings.length === 0 ? (
            <div style={{ color: '#8b949e', fontSize: '14px', fontStyle: 'italic' }}>
              No critical package risks discovered!
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {analysis.findings.map((finding, idx) => {
                const isOverridden = currentOverrides.includes(finding.package_name);
                const badgeColor = finding.severity === 'CRITICAL' ? '#f85149' : finding.severity === 'HIGH' ? '#ff7b72' : '#d29922';

                return (
                  <div key={idx} style={{
                    backgroundColor: '#0d1117',
                    border: '1px solid #30363d',
                    borderRadius: '6px',
                    padding: '12px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                    opacity: isOverridden ? 0.5 : 1
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 'bold', fontSize: '13px', color: '#c9d1d9', wordBreak: 'break-all' }}>
                        {finding.app_name || finding.package_name}
                      </span>
                      <span style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        borderRadius: '4px',
                        backgroundColor: badgeColor + '20',
                        border: `1px solid ${badgeColor}`,
                        color: badgeColor,
                        fontWeight: 'bold'
                      }}>
                        {finding.severity}
                      </span>
                    </div>

                    <div style={{ fontSize: '12px', color: '#8b949e' }}>
                      <strong>Package:</strong> {finding.package_name}
                    </div>

                    <div style={{ fontSize: '12px', color: '#8b949e', lineHeight: '1.4' }}>
                      {finding.reasoning}
                    </div>

                    {/* Override action switch */}
                    <button
                      onClick={() => handleToggleOverride(finding.package_name)}
                      style={{
                        alignSelf: 'flex-end',
                        padding: '4px 8px',
                        backgroundColor: isOverridden ? '#238636' : 'transparent',
                        border: `1px solid ${isOverridden ? '#2ea043' : '#30363d'}`,
                        color: isOverridden ? '#fff' : '#8b949e',
                        borderRadius: '4px',
                        fontSize: '11px',
                        cursor: 'pointer',
                        fontWeight: 'bold'
                      }}
                    >
                      {isOverridden ? '✓ Excluded (Score Penalty Lifted)' : 'Exclude Risk'}
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Actionable Recommendations Checklist */}
        <div style={{
          backgroundColor: '#161b22',
          border: '1px solid #30363d',
          borderRadius: '8px',
          padding: '20px',
          maxHeight: '400px',
          overflowY: 'auto'
        }}>
          <h3 style={{ margin: '0 0 15px 0', fontSize: '16px', color: '#58a6ff' }}>Actionable Recommendations</h3>

          {analysis.recovery_sequence.length === 0 ? (
            <div style={{ color: '#8b949e', fontSize: '14px', fontStyle: 'italic' }}>
              No actions required.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {analysis.recovery_sequence.map((action) => {
                const isChecked = !!completedActions[action.action_id];
                
                return (
                  <div
                    key={action.action_id}
                    onClick={() => handleToggleAction(action.action_id)}
                    style={{
                      backgroundColor: isChecked ? '#1c2024' : '#0d1117',
                      border: `1px solid ${isChecked ? '#1f6feb' : '#30363d'}`,
                      borderRadius: '6px',
                      padding: '12px',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '12px',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}} // Swapped via div click handler
                      style={{ marginTop: '3px', cursor: 'pointer' }}
                    />
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div style={{
                        fontWeight: 'bold',
                        fontSize: '13px',
                        color: isChecked ? '#8b949e' : '#c9d1d9',
                        textDecoration: isChecked ? 'line-through' : 'none'
                      }}>
                        {action.title}
                      </div>
                      <div style={{
                        fontSize: '12px',
                        color: '#8b949e',
                        lineHeight: '1.4',
                        textDecoration: isChecked ? 'line-through' : 'none'
                      }}>
                        {action.description}
                      </div>
                      <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                        <span style={{ fontSize: '10px', color: '#58a6ff', backgroundColor: '#388bfd15', padding: '1px 5px', borderRadius: '4px' }}>
                          Priority {action.priority}
                        </span>
                        <span style={{ fontSize: '10px', color: '#d29922', backgroundColor: '#d2992215', padding: '1px 5px', borderRadius: '4px' }}>
                          {action.category}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Action Bar */}
      <div style={{
        backgroundColor: '#161b22',
        border: '1px solid #30363d',
        borderRadius: '8px',
        padding: '15px 20px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '10px'
      }}>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            onClick={handleExportHtml}
            disabled={exportingHtml || exportingPdf}
            style={{
              padding: '10px 18px',
              backgroundColor: '#21262d',
              border: '1px solid #30363d',
              color: '#c9d1d9',
              fontWeight: 'bold',
              borderRadius: '6px',
              cursor: exportingHtml || exportingPdf ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
              fontSize: '13px'
            }}
            onMouseOver={(e) => { if (!exportingHtml && !exportingPdf) e.currentTarget.style.backgroundColor = '#30363d'; }}
            onMouseOut={(e) => { if (!exportingHtml && !exportingPdf) e.currentTarget.style.backgroundColor = '#21262d'; }}
          >
            {exportingHtml ? 'Exporting HTML...' : 'Export HTML Report'}
          </button>
          
          <button
            onClick={handleExportPdf}
            disabled={exportingHtml || exportingPdf}
            style={{
              padding: '10px 18px',
              backgroundColor: '#21262d',
              border: '1px solid #30363d',
              color: '#c9d1d9',
              fontWeight: 'bold',
              borderRadius: '6px',
              cursor: exportingHtml || exportingPdf ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.2s',
              fontSize: '13px'
            }}
            onMouseOver={(e) => { if (!exportingHtml && !exportingPdf) e.currentTarget.style.backgroundColor = '#30363d'; }}
            onMouseOut={(e) => { if (!exportingHtml && !exportingPdf) e.currentTarget.style.backgroundColor = '#21262d'; }}
          >
            {exportingPdf ? 'Exporting PDF...' : 'Export PDF Report'}
          </button>
        </div>

        <button
          onClick={onReset}
          style={{
            padding: '10px 18px',
            backgroundColor: '#1f6feb',
            border: 'none',
            color: '#fff',
            fontWeight: 'bold',
            borderRadius: '6px',
            cursor: 'pointer',
            transition: 'background-color 0.2s',
            fontSize: '13px'
          }}
          onMouseOver={(e) => e.currentTarget.style.backgroundColor = '#388bfd'}
          onMouseOut={(e) => e.currentTarget.style.backgroundColor = '#1f6feb'}
        >
          Reset / New Scan
        </button>
      </div>
    </div>
  );
}

export default AssessmentResults;
