// API Service for AI Council

export interface ProviderConfig {
  id: string;
  display_name: string;
  is_enabled: boolean;
  default_mode: 'manual' | 'api';
  official_url: string;
  api_key_configured: boolean;
  selected_model: string;
  supported_models: string[];
  usage_limit_monthly_usd: number;
  current_month_usage_usd: number;
  is_verified: boolean;
  last_checked_at: string | null;
}

export interface ModelResponse {
  id: string;
  run_id: string;
  round_id: string | null;
  provider: string;
  model_id: string | null;
  stage: string;
  integration_mode: 'manual' | 'api';
  prompt_used: string;
  content: string;
  status: 'pending' | 'completed' | 'failed';
  error_message: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  created_at: string;
}

export interface Critique {
  id: string;
  run_id: string;
  round_id: string | null;
  reviewer_provider: string;
  target_provider: string;
  content: string;
  unsupported_claims: string[];
  contradictions: string[];
  hidden_assumptions: string[];
  logical_fallacies: string[];
  risks_limitations: string[];
  status: string;
  created_at: string;
}

export interface Synthesis {
  id: string;
  run_id: string;
  round_id: string | null;
  moderator_provider: string;
  mode: string;
  problem_summary: string | null;
  consensus_points: string | null;
  disagreements: string | null;
  unresolved_critiques: string | null;
  evidence_backed_claims: string | null;
  recommendations: string | null;
  uncertainties_and_verifications: string | null;
  references_cited: string | null;
  raw_synthesis: string;
  created_at: string;
}

export interface SourceReference {
  id: string;
  run_id: string;
  document_id: string | null;
  chunk_id: string | null;
  quote: string;
  page_number: number;
  relevance_score: number;
  is_verified: boolean;
  source_type: string;
}

export interface DiscussionRun {
  id: string;
  conversation_id: string;
  mode: 'parallel' | 'debate' | 'research';
  status: 'pending' | 'in_progress' | 'awaiting_input' | 'completed' | 'failed' | 'stopped';
  current_stage: 'parallel_analysis' | 'initial_analysis' | 'cross_critique' | 'rebuttal' | 'final_synthesis' | 'completed';
  current_round: number;
  max_rounds: number;
  query: string;
  selected_providers: string[];
  linked_document_ids: string[];
  created_at: string;
  updated_at: string;
  responses: ModelResponse[];
  critiques: Critique[];
  syntheses: Synthesis[];
  source_references: SourceReference[];
}

export interface DocumentItem {
  id: string;
  project_id: string | null;
  filename: string;
  original_name: string;
  file_type: string;
  file_size_bytes: number;
  title: string;
  total_pages: number;
  total_chunks: number;
  created_at: string;
}

export interface DocumentSearchResult {
  document_id: string;
  chunk_id: string;
  document_title: string;
  page_number: number;
  content: string;
  relevance_score: number;
  is_verified: boolean;
}

export interface ResearchProject {
  id: string;
  title: string;
  description: string | null;
  research_question: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationItem {
  id: string;
  project_id: string | null;
  title: string;
  mode: string;
  created_at: string;
  updated_at: string;
}

export interface UsageSummary {
  total_requests: number;
  manual_requests: number;
  api_requests: number;
  total_tokens: number;
  estimated_total_cost_usd: number;
  by_provider: Record<string, {
    display_name: string;
    default_mode: string;
    api_configured: boolean;
    requests_count: number;
    tokens: number;
    estimated_cost_usd: number;
    monthly_limit_usd: number;
  }>;
}

const API_BASE = '/api';

export const api = {
  // Health
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    return res.json();
  },

  // Discussions
  async createDiscussion(data: {
    query: string;
    mode: string;
    selected_providers: string[];
    max_rounds?: number;
    project_id?: string;
    linked_document_ids?: string[];
    conversation_title?: string;
  }): Promise<DiscussionRun> {
    const res = await fetch(`${API_BASE}/discussions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Gagal memulai diskusi');
    }
    return res.json();
  },

  async getDiscussion(runId: string): Promise<DiscussionRun> {
    const res = await fetch(`${API_BASE}/discussions/${runId}`);
    if (!res.ok) throw new Error('Sesi diskusi tidak ditemukan');
    return res.json();
  },

  async submitManualResponse(runId: string, data: {
    response_id: string;
    content: string;
    model_id?: string;
    status?: string;
  }): Promise<ModelResponse> {
    const res = await fetch(`${API_BASE}/discussions/${runId}/responses`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Gagal mengirim respons');
    }
    return res.json();
  },

  async advanceDebateStage(runId: string): Promise<DiscussionRun> {
    const res = await fetch(`${API_BASE}/discussions/${runId}/advance`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Gagal melanjutkan tahapan debat');
    }
    return res.json();
  },

  async submitSynthesis(runId: string, data: {
    raw_synthesis: string;
    moderator_provider?: string;
    allow_partial?: boolean;
    problem_summary?: string;
    consensus_points?: string;
    disagreements?: string;
    unresolved_critiques?: string;
    evidence_backed_claims?: string;
    recommendations?: string;
    uncertainties_and_verifications?: string;
    references_cited?: string;
  }) {
    const res = await fetch(`${API_BASE}/discussions/${runId}/synthesis`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ run_id: runId, ...data }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Gagal menyimpan sintesis moderator');
    }
    return res.json();
  },

  async stopDiscussion(runId: string): Promise<DiscussionRun> {
    const res = await fetch(`${API_BASE}/discussions/${runId}/stop`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Gagal menghentikan diskusi');
    }
    return res.json();
  },

  async resumeDiscussion(runId: string): Promise<DiscussionRun> {
    const res = await fetch(`${API_BASE}/discussions/${runId}/resume`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Gagal melanjutkan diskusi');
    }
    return res.json();
  },

  async continueToDebate(runId: string): Promise<DiscussionRun> {
    const res = await fetch(`${API_BASE}/discussions/${runId}/continue-to-debate`, {
      method: 'POST',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Gagal melanjutkan ke AI Debate');
    }
    return res.json();
  },

  getExportUrl(runId: string, format: 'md' | 'txt' = 'md'): string {
    return `${API_BASE}/discussions/${runId}/export?format=${format}`;
  },

  async downloadExportReport(runId: string, format: 'md' | 'txt' = 'md'): Promise<void> {
    const res = await fetch(`${API_BASE}/discussions/${runId}/export?format=${format}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Gagal mengunduh laporan diskusi');
    }
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ai_council_report_${runId.slice(0, 8)}.${format}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  },

  // Conversations
  async getConversations(projectId?: string): Promise<ConversationItem[]> {
    const url = projectId ? `${API_BASE}/conversations?project_id=${projectId}` : `${API_BASE}/conversations`;
    const res = await fetch(url);
    return res.json();
  },

  async deleteConversation(id: string) {
    const res = await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' });
    return res.json();
  },

  // Providers
  async getProviders(): Promise<ProviderConfig[]> {
    const res = await fetch(`${API_BASE}/providers`);
    return res.json();
  },

  async updateProvider(id: string, data: Partial<ProviderConfig> & { api_key?: string }): Promise<ProviderConfig> {
    const res = await fetch(`${API_BASE}/providers/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Gagal memperbarui provider');
    }
    return res.json();
  },

  async testProvider(id: string, data?: { api_key?: string; model?: string }) {
    const res = await fetch(`${API_BASE}/providers/${id}/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data || {}),
    });
    return res.json();
  },

  // Documents
  async getDocuments(projectId?: string): Promise<DocumentItem[]> {
    const url = projectId ? `${API_BASE}/documents?project_id=${projectId}` : `${API_BASE}/documents`;
    const res = await fetch(url);
    return res.json();
  },

  async uploadDocument(file: File, title?: string, projectId?: string): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append('file', file);
    if (title) formData.append('title', title);
    if (projectId) formData.append('project_id', projectId);

    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Gagal mengunggah dokumen');
    }
    return res.json();
  },

  async deleteDocument(id: string) {
    const res = await fetch(`${API_BASE}/documents/${id}`, { method: 'DELETE' });
    return res.json();
  },

  async searchDocuments(query: string, documentIds?: string[]): Promise<DocumentSearchResult[]> {
    const res = await fetch(`${API_BASE}/documents/search?query=${encodeURIComponent(query)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, document_ids: documentIds }),
    });
    return res.json();
  },

  // Research Projects
  async getProjects(): Promise<ResearchProject[]> {
    const res = await fetch(`${API_BASE}/research/projects`);
    return res.json();
  },

  async createProject(data: Partial<ResearchProject>): Promise<ResearchProject> {
    const res = await fetch(`${API_BASE}/research/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Gagal membuat proyek');
    return res.json();
  },

  async deleteProject(id: string) {
    const res = await fetch(`${API_BASE}/research/projects/${id}`, { method: 'DELETE' });
    return res.json();
  },

  async getNotebookLMPrompt(researchQuestion: string, notes?: string) {
    const params = new URLSearchParams({ research_question: researchQuestion });
    if (notes) params.append('notes', notes);
    const res = await fetch(`${API_BASE}/research/notebooklm-prompt?${params.toString()}`);
    return res.json();
  },

  // Usage
  async getUsageSummary(): Promise<UsageSummary> {
    const res = await fetch(`${API_BASE}/usage/summary`);
    return res.json();
  },

  async getUsageRecords(limit: number = 50) {
    const res = await fetch(`${API_BASE}/usage/records?limit=${limit}`);
    return res.json();
  },
};
