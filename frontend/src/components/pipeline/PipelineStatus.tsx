import type { ProjectRun } from '../../types/api';
import { useEffect, useState } from 'react';

interface Props {
  run: ProjectRun;
  projectId: string;
}

const STEP_NAMES: Record<string, string> = {
  ingest: '📥 素材导入',
  transcribe: '🎤 语音转录',
  extract_features: '🎵 特征提取',
  chunk_and_screen: '📊 分块筛选',
  generate_candidates: '✨ 生成候选',
  multimodal_review: '🎬 多模态复审',
};

const STEP_DESCRIPTIONS: Record<string, string> = {
  ingest: '正在读取视频信息并提取音频...',
  transcribe: '正在将音频转换为文字（这可能需要较长时间）...',
  extract_features: '正在分析音频的音量、节奏等特征...',
  chunk_and_screen: '正在将视频分块并进行初步筛选...',
  generate_candidates: '正在生成高质量候选片段...',
  multimodal_review: '正在使用 AI 分析视频内容...',
};

export function PipelineStatus({ run, projectId }: Props) {
  const [logs, setLogs] = useState<string[]>([]);
  const [autoScroll, setAutoScroll] = useState(true);

  // 轮询获取日志
  useEffect(() => {
    if (run.status !== 'running') return;

    const interval = setInterval(async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/pipeline/${projectId}/runs/${run.id}/logs`);
        if (response.ok) {
          const data = await response.json();
          setLogs(data.logs || []);
        }
      } catch (error) {
        console.error('获取日志失败:', error);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [run.status, projectId, run.id]);

  // 自动滚动到底部
  useEffect(() => {
    if (autoScroll) {
      const logContainer = document.getElementById('log-container');
      if (logContainer) {
        logContainer.scrollTop = logContainer.scrollHeight;
      }
    }
  }, [logs, autoScroll]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#28a745';
      case 'running': return '#007bff';
      case 'failed': return '#dc3545';
      default: return '#6c757d';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'completed': return '✓ 完成';
      case 'running': return '⟳ 运行中';
      case 'failed': return '✗ 失败';
      default: return '○ 等待';
    }
  };

  const currentStep = run.steps.find(s => s.status === 'running');

  return (
    <div style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '20px', backgroundColor: '#f8f9fa' }}>
      <div style={{ marginBottom: '15px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <strong>运行状态:</strong>{' '}
          <span style={{ color: getStatusColor(run.status), fontSize: '18px', fontWeight: 'bold' }}>
            {run.status === 'running' ? '🔄 运行中' : run.status === 'completed' ? '✅ 已完成' : run.status === 'failed' ? '❌ 失败' : '⏸️ 等待'}
          </span>
        </div>
        {run.started_at && (
          <div style={{ fontSize: '14px', color: '#6c757d' }}>
            开始时间: {new Date(run.started_at).toLocaleString('zh-CN')}
          </div>
        )}
      </div>

      {currentStep && (
        <div style={{ marginBottom: '15px', padding: '15px', backgroundColor: '#e7f3ff', borderRadius: '6px', border: '2px solid #007bff' }}>
          <div style={{ fontSize: '16px', fontWeight: 'bold', marginBottom: '5px' }}>
            {STEP_NAMES[currentStep.step_name] || currentStep.step_name}
          </div>
          <div style={{ fontSize: '14px', color: '#495057' }}>
            {STEP_DESCRIPTIONS[currentStep.step_name] || '正在处理...'}
          </div>
        </div>
      )}

      {run.error_message && (
        <div style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f8d7da', color: '#721c24', borderRadius: '4px' }}>
          <strong>错误:</strong> {run.error_message}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '20px' }}>
        {run.steps.map((step) => (
          <div
            key={step.id}
            style={{
              padding: '15px',
              backgroundColor: 'white',
              borderRadius: '6px',
              border: `2px solid ${getStatusColor(step.status)}`,
              opacity: step.status === 'pending' ? 0.6 : 1,
            }}
          >
            <div style={{ fontWeight: 'bold', marginBottom: '8px' }}>
              {STEP_NAMES[step.step_name] || step.step_name}
            </div>
            <div style={{ fontSize: '14px', color: getStatusColor(step.status), fontWeight: 'bold' }}>
              {getStatusText(step.status)}
            </div>
            {step.started_at && (
              <div style={{ fontSize: '12px', color: '#6c757d', marginTop: '5px' }}>
                {new Date(step.started_at).toLocaleTimeString('zh-CN')}
              </div>
            )}
            {step.error_message && (
              <div style={{ marginTop: '8px', fontSize: '12px', color: '#dc3545' }}>
                {step.error_message}
              </div>
            )}
          </div>
        ))}
      </div>

      {run.status === 'running' && (
        <div style={{ marginTop: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <strong>实时日志:</strong>
            <label style={{ fontSize: '14px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                style={{ marginRight: '5px' }}
              />
              自动滚动
            </label>
          </div>
          <div
            id="log-container"
            style={{
              backgroundColor: '#1e1e1e',
              color: '#d4d4d4',
              padding: '15px',
              borderRadius: '6px',
              fontFamily: 'monospace',
              fontSize: '13px',
              maxHeight: '400px',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {logs.length > 0 ? (
              logs.map((log, i) => (
                <div key={i} style={{ marginBottom: '2px' }}>
                  {log}
                </div>
              ))
            ) : (
              <div style={{ color: '#888' }}>等待日志输出...</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
