import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Project, ProjectRun, Candidate } from '../types/api';
import { PipelineStatus } from '../components/pipeline/PipelineStatus';
import { CandidateList } from '../components/candidate/CandidateList';

export function ProjectDetail() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [runs, setRuns] = useState<ProjectRun[]>([]);
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 3000); // 每3秒刷新
    return () => clearInterval(interval);
  }, [id]);

  const loadData = async () => {
    if (!id) return;
    try {
      const [proj, runsData, candidatesData] = await Promise.all([
        api.getProject(id),
        api.getProjectRuns(id),
        api.getCandidates(id),
      ]);
      setProject(proj);
      setRuns(runsData);
      setCandidates(candidatesData);
      setLoading(false);
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  const handleRunPipeline = async () => {
    if (!id) return;
    try {
      await api.runPipeline(id);
      loadData();
    } catch (err: any) {
      alert('启动失败: ' + err.message);
    }
  };

  const handleExport = async () => {
    if (!id) return;
    try {
      const exp = await api.createExport(id, { format: 'fcpxml', version: '1.13' });
      alert('导出已创建，请稍候...');
      // 轮询导出状态
      const checkExport = setInterval(async () => {
        const exports = await api.listExports(id);
        const current = exports.find(e => e.id === exp.id);
        if (current?.status === 'completed') {
          clearInterval(checkExport);
          api.downloadExport(exp.id);
        } else if (current?.status === 'failed') {
          clearInterval(checkExport);
          alert('导出失败');
        }
      }, 2000);
    } catch (err: any) {
      alert('导出失败: ' + err.message);
    }
  };

  if (loading) return <div style={{ padding: '20px' }}>加载中...</div>;
  if (error) return <div style={{ padding: '20px', color: 'red' }}>错误: {error}</div>;
  if (!project) return <div style={{ padding: '20px' }}>项目不存在</div>;

  const latestRun = runs[0];

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto' }}>
      <div style={{ marginBottom: '20px' }}>
        <Link to="/" style={{ color: '#666', textDecoration: 'none' }}>← 返回项目列表</Link>
      </div>

      <h1>{project.name}</h1>
      <div style={{ marginBottom: '20px', color: '#666' }}>
        <div>视频: {project.source_video_path}</div>
        <div>时长: {project.duration_seconds ? `${(project.duration_seconds / 60).toFixed(1)} 分钟` : '未知'}</div>
        <div>分辨率: {project.width}x{project.height} @ {project.fps?.toFixed(1)} fps</div>
        <div>状态: {project.status}</div>
      </div>

      <div style={{ marginBottom: '30px' }}>
        <button
          onClick={handleRunPipeline}
          disabled={latestRun?.status === 'running'}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            backgroundColor: '#007bff',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: latestRun?.status === 'running' ? 'not-allowed' : 'pointer',
            marginRight: '10px',
          }}
        >
          {latestRun?.status === 'running' ? '运行中...' : '运行 Pipeline'}
        </button>
        <button
          onClick={handleExport}
          disabled={candidates.length === 0}
          style={{
            padding: '10px 20px',
            fontSize: '16px',
            backgroundColor: '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: candidates.length === 0 ? 'not-allowed' : 'pointer',
          }}
        >
          导出 FCPXML
        </button>
      </div>

      {latestRun && (
        <div style={{ marginBottom: '30px' }}>
          <h2>Pipeline 状态</h2>
          <PipelineStatus run={latestRun} projectId={id!} />
        </div>
      )}

      {candidates.length > 0 && (
        <div>
          <h2>候选片段 ({candidates.length})</h2>
          <CandidateList candidates={candidates} onUpdate={loadData} />
        </div>
      )}
    </div>
  );
}
