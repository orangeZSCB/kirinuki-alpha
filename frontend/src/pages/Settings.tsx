import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import type { ProviderConfig } from '../types/api';

export function Settings() {
  const [whisperConfigs, setWhisperConfigs] = useState<ProviderConfig[]>([]);
  const [multimodalConfigs, setMultimodalConfigs] = useState<ProviderConfig[]>([]);
  const [showWhisperForm, setShowWhisperForm] = useState(false);
  const [showMultimodalForm, setShowMultimodalForm] = useState(false);

  const [whisperForm, setWhisperForm] = useState({
    name: '',
    mode: 'local',
    model_size: 'large-v3',
    device: 'cuda',
    base_url: '',
    api_key: '',
    model_request_id: 'whisper-1',
    skip_uvr: false,
    skip_slice: false,
  });

  const [multimodalForm, setMultimodalForm] = useState({
    name: '',
    base_url: '',
    api_key: '',
    model: 'gpt-4-vision-preview',
    provider_type: 'openai_compatible',
    supports_vision: true,
  });

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      const [whisper, multimodal] = await Promise.all([
        api.listProviderConfigs('whisper'),
        api.listProviderConfigs('multimodal'),
      ]);
      setWhisperConfigs(whisper);
      setMultimodalConfigs(multimodal);
    } catch (err) {
      console.error(err);
    }
  };

  const handleCreateWhisper = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      let config;
      if (whisperForm.mode === 'local') {
        config = {
          mode: 'local',
          model_size: whisperForm.model_size,
          device: whisperForm.device,
          compute_type: 'float16',
          language: 'ja',
        };
      } else if (whisperForm.mode === 'gpt_sovits') {
        config = {
          mode: 'gpt_sovits',
          base_url: whisperForm.base_url,
          model_size: whisperForm.model_size,
          skip_uvr: whisperForm.skip_uvr,
          skip_slice: whisperForm.skip_slice,
        };
      } else {
        config = {
          mode: 'remote',
          base_url: whisperForm.base_url,
          api_key: whisperForm.api_key,
          model_request_id: whisperForm.model_request_id,
          endpoint_path: '/audio/transcriptions',
          response_format: 'verbose_json',
        };
      }

      await api.createProviderConfig({
        provider_kind: 'whisper',
        name: whisperForm.name,
        config,
        is_default: whisperConfigs.length === 0,
      });

      setShowWhisperForm(false);
      loadConfigs();
    } catch (err: any) {
      alert('创建失败: ' + err.message);
    }
  };

  const handleCreateMultimodal = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.createProviderConfig({
        provider_kind: 'multimodal',
        name: multimodalForm.name,
        config: {
          provider_type: multimodalForm.provider_type,
          base_url: multimodalForm.base_url,
          api_key: multimodalForm.api_key,
          model: multimodalForm.model,
          timeout_seconds: 120,
          max_frames_per_candidate: 8,
          supports_vision: multimodalForm.supports_vision,
        },
        is_default: multimodalConfigs.length === 0,
      });

      setShowMultimodalForm(false);
      loadConfigs();
    } catch (err: any) {
      alert('创建失败: ' + err.message);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('确定删除此配置？')) return;
    try {
      await api.deleteProviderConfig(id);
      loadConfigs();
    } catch (err: any) {
      alert('删除失败: ' + err.message);
    }
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ marginBottom: '20px' }}>
        <Link to="/" style={{ color: '#666', textDecoration: 'none' }}>← 返回首页</Link>
      </div>

      <h1>设置</h1>

      {/* Whisper 配置 */}
      <div style={{ marginBottom: '40px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h2>Whisper 配置</h2>
          <button
            onClick={() => setShowWhisperForm(true)}
            style={{
              padding: '8px 15px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            添加配置
          </button>
        </div>

        {whisperConfigs.length === 0 ? (
          <div style={{ padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '4px', textAlign: 'center', color: '#666' }}>
            暂无配置
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '10px' }}>
            {whisperConfigs.map((config) => (
              <div key={config.id} style={{ border: '1px solid #ddd', borderRadius: '4px', padding: '15px', backgroundColor: 'white' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div>
                    <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
                      {config.name} {config.is_default && <span style={{ color: '#28a745' }}>(默认)</span>}
                    </div>
                    <div style={{ fontSize: '14px', color: '#666' }}>
                      模式: {config.config.mode === 'local' ? '本地' : config.config.mode === 'gpt_sovits' ? 'GPT-SoVITS' : '远程'}
                      {config.config.mode === 'local' && ` | 模型: ${config.config.model_size}`}
                      {config.config.mode === 'gpt_sovits' && ` | URL: ${config.config.base_url}`}
                      {config.config.mode === 'remote' && ` | URL: ${config.config.base_url}`}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(config.id)}
                    style={{
                      padding: '5px 10px',
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

      {/* 多模态配置 */}
      <div style={{ marginBottom: '40px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h2>多模态模型配置</h2>
          <button
            onClick={() => setShowMultimodalForm(true)}
            style={{
              padding: '8px 15px',
              backgroundColor: '#007bff',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            添加配置
          </button>
        </div>

        {multimodalConfigs.length === 0 ? (
          <div style={{ padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '4px', textAlign: 'center', color: '#666' }}>
            暂无配置
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '10px' }}>
            {multimodalConfigs.map((config) => (
              <div key={config.id} style={{ border: '1px solid #ddd', borderRadius: '4px', padding: '15px', backgroundColor: 'white' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                  <div>
                    <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
                      {config.name} {config.is_default && <span style={{ color: '#28a745' }}>(默认)</span>}
                    </div>
                    <div style={{ fontSize: '14px', color: '#666' }}>
                      URL: {config.config.base_url} | 模型: {config.config.model}
                      {config.config.supports_vision === false && (
                        <span style={{ color: '#ff9800', marginLeft: '8px' }}>
                          | ⚠️ 仅文本模式
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(config.id)}
                    style={{
                      padding: '5px 10px',
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

      {/* Whisper 表单弹窗 */}
      {showWhisperForm && (
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
            maxHeight: '80vh',
            overflow: 'auto',
          }}>
            <h2>添加 Whisper 配置</h2>
            <form onSubmit={handleCreateWhisper}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>配置名称</label>
                <input
                  type="text"
                  value={whisperForm.name}
                  onChange={(e) => setWhisperForm({ ...whisperForm, name: e.target.value })}
                  required
                  style={{ width: '100%', padding: '8px' }}
                />
              </div>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>模式</label>
                <select
                  value={whisperForm.mode}
                  onChange={(e) => setWhisperForm({ ...whisperForm, mode: e.target.value })}
                  style={{ width: '100%', padding: '8px' }}
                >
                  <option value="local">本地 Whisper</option>
                  <option value="remote">远程 Whisper API</option>
                  <option value="gpt_sovits">GPT-SoVITS (UVR5 + 切分 + Whisper)</option>
                </select>
              </div>

              {whisperForm.mode === 'local' ? (
                <>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px' }}>模型大小</label>
                    <select
                      value={whisperForm.model_size}
                      onChange={(e) => setWhisperForm({ ...whisperForm, model_size: e.target.value })}
                      style={{ width: '100%', padding: '8px' }}
                    >
                      <option value="tiny">tiny</option>
                      <option value="base">base</option>
                      <option value="small">small</option>
                      <option value="medium">medium</option>
                      <option value="large-v3">large-v3</option>
                    </select>
                  </div>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px' }}>设备</label>
                    <select
                      value={whisperForm.device}
                      onChange={(e) => setWhisperForm({ ...whisperForm, device: e.target.value })}
                      style={{ width: '100%', padding: '8px' }}
                    >
                      <option value="cuda">CUDA (GPU)</option>
                      <option value="cpu">CPU</option>
                    </select>
                  </div>
                </>
              ) : whisperForm.mode === 'gpt_sovits' ? (
                <>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px' }}>GPT-SoVITS API URL</label>
                    <input
                      type="text"
                      value={whisperForm.base_url}
                      onChange={(e) => setWhisperForm({ ...whisperForm, base_url: e.target.value })}
                      required
                      placeholder="http://localhost:9000"
                      style={{ width: '100%', padding: '8px' }}
                    />
                  </div>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px' }}>Whisper 模型大小</label>
                    <select
                      value={whisperForm.model_size}
                      onChange={(e) => setWhisperForm({ ...whisperForm, model_size: e.target.value })}
                      style={{ width: '100%', padding: '8px' }}
                    >
                      <option value="tiny">tiny</option>
                      <option value="base">base</option>
                      <option value="small">small</option>
                      <option value="medium">medium</option>
                      <option value="large-v3">large-v3</option>
                    </select>
                  </div>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input
                        type="checkbox"
                        checked={whisperForm.skip_uvr}
                        onChange={(e) => setWhisperForm({ ...whisperForm, skip_uvr: e.target.checked })}
                      />
                      跳过 UVR5 人声分离（如果音频已是纯人声）
                    </label>
                  </div>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <input
                        type="checkbox"
                        checked={whisperForm.skip_slice}
                        onChange={(e) => setWhisperForm({ ...whisperForm, skip_slice: e.target.checked })}
                      />
                      跳过语音切分
                    </label>
                  </div>
                </>
              ) : (
                <>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px' }}>Base URL</label>
                    <input
                      type="text"
                      value={whisperForm.base_url}
                      onChange={(e) => setWhisperForm({ ...whisperForm, base_url: e.target.value })}
                      required
                      placeholder="https://api.example.com/v1"
                      style={{ width: '100%', padding: '8px' }}
                    />
                  </div>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px' }}>API Key</label>
                    <input
                      type="password"
                      value={whisperForm.api_key}
                      onChange={(e) => setWhisperForm({ ...whisperForm, api_key: e.target.value })}
                      required
                      style={{ width: '100%', padding: '8px' }}
                    />
                  </div>
                  <div style={{ marginBottom: '15px' }}>
                    <label style={{ display: 'block', marginBottom: '5px' }}>模型 ID</label>
                    <input
                      type="text"
                      value={whisperForm.model_request_id}
                      onChange={(e) => setWhisperForm({ ...whisperForm, model_request_id: e.target.value })}
                      required
                      style={{ width: '100%', padding: '8px' }}
                    />
                  </div>
                </>
              )}

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
                  onClick={() => setShowWhisperForm(false)}
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

      {/* 多模态表单弹窗 */}
      {showMultimodalForm && (
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
            <h2>添加多模态模型配置</h2>
            <form onSubmit={handleCreateMultimodal}>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>配置名称</label>
                <input
                  type="text"
                  value={multimodalForm.name}
                  onChange={(e) => setMultimodalForm({ ...multimodalForm, name: e.target.value })}
                  required
                  style={{ width: '100%', padding: '8px' }}
                />
              </div>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>API 类型</label>
                <select
                  value={multimodalForm.provider_type}
                  onChange={(e) => setMultimodalForm({ ...multimodalForm, provider_type: e.target.value })}
                  style={{ width: '100%', padding: '8px' }}
                >
                  <option value="openai_compatible">OpenAI Compatible (通用)</option>
                  <option value="anthropic">Anthropic (Claude)</option>
                </select>
              </div>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>Base URL</label>
                <input
                  type="text"
                  value={multimodalForm.base_url}
                  onChange={(e) => setMultimodalForm({ ...multimodalForm, base_url: e.target.value })}
                  required
                  placeholder="https://api.example.com/v1"
                  style={{ width: '100%', padding: '8px' }}
                />
              </div>
              <div style={{ marginBottom: '15px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>API Key</label>
                <input
                  type="password"
                  value={multimodalForm.api_key}
                  onChange={(e) => setMultimodalForm({ ...multimodalForm, api_key: e.target.value })}
                  required
                  style={{ width: '100%', padding: '8px' }}
                />
              </div>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', marginBottom: '5px' }}>模型名称</label>
                <input
                  type="text"
                  value={multimodalForm.model}
                  onChange={(e) => setMultimodalForm({ ...multimodalForm, model: e.target.value })}
                  required
                  placeholder="gpt-4-vision-preview"
                  style={{ width: '100%', padding: '8px' }}
                />
              </div>

              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={multimodalForm.supports_vision}
                    onChange={(e) => setMultimodalForm({ ...multimodalForm, supports_vision: e.target.checked })}
                    style={{ marginRight: '8px' }}
                  />
                  <span>支持多模态（图片）分析</span>
                </label>
                {!multimodalForm.supports_vision && (
                  <div style={{
                    marginTop: '8px',
                    padding: '10px',
                    backgroundColor: '#fff3cd',
                    border: '1px solid #ffc107',
                    borderRadius: '4px',
                    fontSize: '14px',
                    color: '#856404'
                  }}>
                    ⚠️ 关闭多模态分析将仅使用纯文本分析，可能降低识别准确度
                  </div>
                )}
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
                  onClick={() => setShowMultimodalForm(false)}
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
    </div>
  );
}
