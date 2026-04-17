import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { Project } from '../types/api';

export function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    source_video_path: '',
    language: 'ja',
  });

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const data = await api.listProjects();
      setProjects(data);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createProject(newProject);
      setShowCreate(false);
      setNewProject({ name: '', source_video_path: '', language: 'ja' });
      loadProjects();
    } catch (err: any) {
      alert('创建失败: ' + err.message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此项目？')) return;
    try {
      await api.deleteProject(id);
      loadProjects();
    } catch (err: any) {
      alert('删除失败: ' + err.message);
    }
  };

  if (loading) return <div style={{ padding: '20px' }}>加载中...</div>;

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '30px' }}>
        <h1>KiriNuki - 项目列表</h1>
        <div>
          <Link to="/settings" style={{ marginRight: '15px', color: '#666' }}>设置</Link>
          <button
            onClick={() => setShowCreate(true)}
            style={{
              padding: '10px 20px',
              fontSize: '16px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            新建项目
          </button>
        </div>
      </div>

      {showCreate && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '8px',
            width: '500px',
          }}>
            <h2>新建项目</h2>
            <form onSubmit={handleCreate}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>项目名称</label>
                <input
                  type="text"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  required
                  style={{ width: '100%', padding: '8px', fontSize: '14px' }}
                />
              </div>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>视频文件路径</label>
                <input
                  type="text"
                  value={newProject.source_video_path}
                  onChange={(e) => setNewProject({ ...newProject, source_video_path: e.target.value })}
                  required
                  placeholder="/path/to/video.mp4"
                  style={{ width: '100%', padding: '8px', fontSize: '14px' }}
                />
              </div>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>语言</label>
                <select
                  value={newProject.language}
                  onChange={(e) => setNewProject({ ...newProject, language: e.target.value })}
                  style={{ width: '100%', padding: '8px', fontSize: '14px' }}
                >
                  <option value="ja">日语</option>
                  <option value="zh">中文</option>
                  <option value="en">英语</option>
                </select>
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  type="submit"
                  style={{
                    flex: 1,
                    padding: '10px',
                    backgroundColor: '#007bff',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  创建
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  style={{
                    flex: 1,
                    padding: '10px',
                    backgroundColor: '#6c757d',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  取消
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {projects.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px', color: '#999' }}>
          暂无项目，点击"新建项目"开始
        </div>
      ) : (
        <div style={{ display: 'grid', gap: '20px' }}>
          {projects.map((project) => (
            <div
              key={project.id}
              style={{
                border: '1px solid #ddd',
                borderRadius: '8px',
                padding: '20px',
                backgroundColor: 'white',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div style={{ flex: 1 }}>
                  <Link
                    to={`/projects/${project.id}`}
                    style={{ fontSize: '20px', fontWeight: 'bold', color: '#007bff', textDecoration: 'none' }}
                  >
                    {project.name}
                  </Link>
                  <div style={{ marginTop: '10px', color: '#666', fontSize: '14px' }}>
                    <div>视频: {project.source_video_path}</div>
                    <div>时长: {project.duration_seconds ? `${(project.duration_seconds / 60).toFixed(1)} 分钟` : '未知'}</div>
                    <div>状态: <span style={{
                      padding: '2px 8px',
                      borderRadius: '4px',
                      backgroundColor: project.status === 'completed' ? '#d4edda' : '#fff3cd',
                      color: project.status === 'completed' ? '#155724' : '#856404',
                    }}>{project.status}</span></div>
                    <div>创建时间: {new Date(project.created_at).toLocaleString('zh-CN')}</div>
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(project.id)}
                  style={{
                    padding: '5px 15px',
                    backgroundColor: '#dc3545',
                    color: 'white',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    fontSize: '14px',
                  }}
                >
                  删除
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
