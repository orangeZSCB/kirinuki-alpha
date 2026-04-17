import { useState } from 'react';
import type { Candidate } from '../../types/api';
import { api } from '../../api/client';

interface Props {
  candidates: Candidate[];
  onUpdate: () => void;
}

export function CandidateList({ candidates, onUpdate }: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleKeep = async (id: string) => {
    try {
      await api.updateCandidate(id, { manual_keep: true, manual_reject: false });
      onUpdate();
    } catch (err: any) {
      alert('更新失败: ' + err.message);
    }
  };

  const handleReject = async (id: string) => {
    try {
      await api.updateCandidate(id, { manual_reject: true, manual_keep: false });
      onUpdate();
    } catch (err: any) {
      alert('更新失败: ' + err.message);
    }
  };

  const handleSaveTitle = async (id: string) => {
    try {
      await api.updateCandidate(id, { title: editTitle });
      setEditingId(null);
      onUpdate();
    } catch (err: any) {
      alert('更新失败: ' + err.message);
    }
  };

  return (
    <div style={{ display: 'grid', gap: '15px' }}>
      {candidates.map((candidate) => (
        <div
          key={candidate.id}
          style={{
            border: '1px solid #ddd',
            borderRadius: '8px',
            padding: '15px',
            backgroundColor: candidate.manual_reject ? '#f8d7da' : candidate.manual_keep ? '#d4edda' : 'white',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
            <div style={{ flex: 1 }}>
              {editingId === candidate.id ? (
                <div style={{ marginBottom: '10px' }}>
                  <input
                    type="text"
                    value={editTitle}
                    onChange={(e) => setEditTitle(e.target.value)}
                    style={{ width: '100%', padding: '5px', fontSize: '16px' }}
                  />
                  <div style={{ marginTop: '5px' }}>
                    <button
                      onClick={() => handleSaveTitle(candidate.id)}
                      style={{ marginRight: '5px', padding: '5px 10px' }}
                    >
                      保存
                    </button>
                    <button onClick={() => setEditingId(null)} style={{ padding: '5px 10px' }}>
                      取消
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '10px', cursor: 'pointer' }}
                  onClick={() => {
                    setEditingId(candidate.id);
                    setEditTitle(candidate.title || '');
                  }}
                >
                  {candidate.title || '未命名片段'} ✏️
                </div>
              )}

              <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>
                <strong>时间:</strong> {formatTime(candidate.start_seconds)} - {formatTime(candidate.end_seconds)} ({candidate.duration_seconds.toFixed(1)}秒)
              </div>

              {candidate.summary && (
                <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>
                  <strong>摘要:</strong> {candidate.summary}
                </div>
              )}

              <div style={{ fontSize: '14px', color: '#666', marginBottom: '8px' }}>
                <strong>得分:</strong>{' '}
                {candidate.heuristic_score !== null && candidate.heuristic_score !== undefined && `音频 ${candidate.heuristic_score.toFixed(1)} | `}
                {candidate.cheap_model_score !== null && candidate.cheap_model_score !== undefined && `文本 ${candidate.cheap_model_score.toFixed(1)} | `}
                {candidate.multimodal_score !== null && candidate.multimodal_score !== undefined && `多模态 ${candidate.multimodal_score.toFixed(1)} | `}
                {candidate.final_score !== null && candidate.final_score !== undefined && `总分 ${candidate.final_score.toFixed(1)}`}
              </div>

              {candidate.tags && candidate.tags.length > 0 && (
                <div style={{ marginTop: '8px' }}>
                  {candidate.tags.map((tag, idx) => (
                    <span
                      key={idx}
                      style={{
                        display: 'inline-block',
                        padding: '2px 8px',
                        marginRight: '5px',
                        backgroundColor: '#e9ecef',
                        borderRadius: '4px',
                        fontSize: '12px',
                      }}
                    >
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div style={{ display: 'flex', gap: '5px', marginLeft: '15px' }}>
              <button
                onClick={() => handleKeep(candidate.id)}
                disabled={candidate.manual_keep}
                style={{
                  padding: '8px 15px',
                  backgroundColor: candidate.manual_keep ? '#28a745' : '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: candidate.manual_keep ? 'default' : 'pointer',
                  fontSize: '14px',
                }}
              >
                {candidate.manual_keep ? '✓ 已保留' : '保留'}
              </button>
              <button
                onClick={() => handleReject(candidate.id)}
                disabled={candidate.manual_reject}
                style={{
                  padding: '8px 15px',
                  backgroundColor: candidate.manual_reject ? '#dc3545' : '#6c757d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: candidate.manual_reject ? 'default' : 'pointer',
                  fontSize: '14px',
                }}
              >
                {candidate.manual_reject ? '✗ 已拒绝' : '拒绝'}
              </button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
