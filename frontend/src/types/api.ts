// API 类型定义
export interface Project {
  id: string;
  name: string;
  source_video_path: string;
  language: string;
  status: string;
  duration_seconds?: number;
  fps?: number;
  width?: number;
  height?: number;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  source_video_path: string;
  language?: string;
}

export interface PipelineStep {
  id: string;
  step_name: string;
  status: string;
  progress: number;
  started_at?: string;
  finished_at?: string;
  error_message?: string;
}

export interface ProjectRun {
  id: string;
  project_id: string;
  status: string;
  started_at?: string;
  finished_at?: string;
  error_message?: string;
  steps: PipelineStep[];
}

export interface Candidate {
  id: string;
  project_id: string;
  start_seconds: number;
  end_seconds: number;
  duration_seconds: number;
  heuristic_score?: number;
  cheap_model_score?: number;
  multimodal_score?: number;
  final_score?: number;
  title?: string;
  summary?: string;
  tags?: string[];
  status: string;
  manual_keep?: boolean;
  manual_reject?: boolean;
  keyframes?: string[];
  created_at: string;
}

export interface CandidateUpdate {
  start_seconds?: number;
  end_seconds?: number;
  title?: string;
  manual_keep?: boolean;
  manual_reject?: boolean;
}

export interface Export {
  id: string;
  project_id: string;
  format: string;
  version?: string;
  status: string;
  file_path?: string;
  created_at: string;
}

export interface ExportCreate {
  format: string;
  version?: string;
}

export interface ProviderConfig {
  id: string;
  provider_kind: string;
  name: string;
  config: Record<string, any>;
  is_default: boolean;
  created_at: string;
}

export interface ProviderConfigCreate {
  provider_kind: string;
  name: string;
  config: Record<string, any>;
  is_default: boolean;
}

export interface IrasutoyaImage {
  title: string;
  imageUrl: string;
  description: string;
  categories: string[];
}
