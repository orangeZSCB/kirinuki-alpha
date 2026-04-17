import type {
  Project,
  ProjectCreate,
  ProjectRun,
  Candidate,
  CandidateUpdate,
  Export,
  ExportCreate,
  ProviderConfig,
  ProviderConfigCreate,
  IrasutoyaImage,
} from '../types/api';

const API_BASE = 'http://localhost:8000/api';

class ApiClient {
  // Projects
  async createProject(data: ProjectCreate): Promise<Project> {
    const res = await fetch(`${API_BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async listProjects(): Promise<Project[]> {
    const res = await fetch(`${API_BASE}/projects`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async getProject(id: string): Promise<Project> {
    const res = await fetch(`${API_BASE}/projects/${id}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async deleteProject(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/projects/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
  }

  // Pipeline
  async runPipeline(projectId: string): Promise<ProjectRun> {
    const res = await fetch(`${API_BASE}/pipeline/${projectId}/run`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async getProjectRuns(projectId: string): Promise<ProjectRun[]> {
    const res = await fetch(`${API_BASE}/pipeline/${projectId}/runs`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async getRunDetail(runId: string): Promise<ProjectRun> {
    const res = await fetch(`${API_BASE}/pipeline/runs/${runId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  // Candidates
  async getCandidates(projectId: string): Promise<Candidate[]> {
    const res = await fetch(`${API_BASE}/candidates/${projectId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async updateCandidate(id: string, data: CandidateUpdate): Promise<Candidate> {
    const res = await fetch(`${API_BASE}/candidates/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  // Exports
  async createExport(projectId: string, data: ExportCreate): Promise<Export> {
    const res = await fetch(`${API_BASE}/exports/${projectId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async listExports(projectId: string): Promise<Export[]> {
    const res = await fetch(`${API_BASE}/exports/${projectId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async downloadExport(exportId: string): Promise<void> {
    window.open(`${API_BASE}/exports/${exportId}/download`, '_blank');
  }

  // Provider configs
  async createProviderConfig(data: ProviderConfigCreate): Promise<ProviderConfig> {
    const res = await fetch(`${API_BASE}/settings/providers`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async listProviderConfigs(kind?: string): Promise<ProviderConfig[]> {
    const url = kind
      ? `${API_BASE}/settings/providers?provider_kind=${kind}`
      : `${API_BASE}/settings/providers`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async deleteProviderConfig(id: string): Promise<void> {
    const res = await fetch(`${API_BASE}/settings/providers/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(await res.text());
  }

  // irasutoya
  async searchIrasutoya(query: string): Promise<IrasutoyaImage[]> {
    const res = await fetch(`${API_BASE}/irasutoya/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async randomIrasutoya(): Promise<IrasutoyaImage> {
    const res = await fetch(`${API_BASE}/irasutoya/random`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
}

export const api = new ApiClient();
