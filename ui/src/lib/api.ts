// API service module for BioDockify pharmaceutical research platform
// All API calls are relative - the gateway handles routing

export const API_BASE = '/api';

export interface ResearchStatus {
  taskId: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  currentStep: number;
  logs: string[];
  phase: string;
}

export interface ResearchResults {
  taskId: string;
  title: string;
  stats: {
    papers: number;
    entities: number;
    nodes: number;
    connections: number;
  };
  entities: {
    drugs: string[];
    diseases: string[];
    proteins: string[];
  };
  summary: string;
}

export interface Project {
  id: string;
  title: string;
  type: 'research' | 'lab_experiment' | 'clinical_trial';
  status: 'pending' | 'planning' | 'executing' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  updated_at: string;
}

export interface EnhancedSystemStatus {
  status: 'online' | 'degraded' | 'offline';
  scheduler_mode: string;
  active_projects: number;
  total_projects: number;
  device_count: number;
  queue_size: number;
}

export interface ProtocolRequest {
  taskId: string;
  type: 'liquid-handler' | 'crystallization' | 'assay';
}

export interface ReportRequest {
  taskId: string;
  template: 'full' | 'summary' | 'executive';
}

export type UserRole = 'PhD Student' | 'PG Student' | 'Senior Researcher' | 'Industry Scientist' | 'Researcher' | 'Student' | 'Lab Tech' | 'Clinician' | 'Faculty' | 'Receptionist';

export interface Settings {
  project: {
    name: string;
    type: string;
    disease_context: string;
    stage: string;
  };
  agent: {
    mode: 'assisted' | 'semi-autonomous' | 'autonomous';
    reasoning_depth: 'shallow' | 'standard' | 'deep';
    self_correction: boolean;
    max_retries: number;
    failure_policy: 'ask_user' | 'auto_retry' | 'abort';
    max_runtime_minutes?: number; // V2: Execution Limit
    use_knowledge_graph?: boolean; // V2: Neo4j Integration
    human_approval_gates?: boolean; // V2: Safety/Consent Switch
  };
  // Agent Zero (Research Agent) Settings
  agent_zero?: {
    autonomy_level?: string;
    force_persona?: string;
    internet_research?: boolean;
    // Add other properties as needed
  };
  nanobot?: {
    headless_browser?: boolean;
    stealth_mode?: boolean;
    browser_timeout?: number;
  };
  literature: {
    sources: string[];
    enable_crossref: boolean;
    enable_preprints: boolean;
    year_range: number;
    novelty_strictness: 'low' | 'medium' | 'high';
    grobid_url?: string; // V2: GROBID Analysis
  };
  channels?: {
    telegram?: { enabled: boolean; token: string; allow_from: string[] };
    whatsapp?: { enabled: boolean; bridge_url: string; auth_token: string; allow_from: string[] };
    discord?: { enabled: boolean; token: string; allow_from: string[]; gateway_url: string };
  };
  ai_provider: {
    mode: 'google' | 'openai' | 'anthropic' | 'deepseek' | 'openrouter' | 'groq' | 'huggingface' | 'ollama' | 'glm' | 'kimi' | 'custom' | 'surfsense' | 'azure' | 'aws' | 'mistral' | 'venice';

    // Ollama (Local)
    ollama_url?: string;
    ollama_model?: string;

    // FREE APIs
    google_key?: string;
    google_model?: string;
    huggingface_key?: string;
    huggingface_model?: string;
    groq_key?: string;
    groq_model?: string;

    // PAID APIs
    openrouter_key?: string;
    openrouter_model?: string;
    deepseek_key?: string;
    deepseek_model?: string;
    glm_key?: string;
    glm_model?: string;
    openai_key?: string;
    openai_model?: string;
    anthropic_key?: string;
    anthropic_model?: string;

    // NEW: Expanded Providers
    mistral_key?: string;
    mistral_model?: string;
    venice_key?: string;
    venice_model?: string;
    kimi_key?: string;
    kimi_model?: string;

    // NEW: Cloud Enterprise
    azure_endpoint?: string;
    azure_deployment?: string;
    azure_key?: string;
    azure_api_version?: string;

    aws_access_key?: string;
    aws_secret_key?: string;
    aws_region_name?: string;
    aws_model_id?: string;

    // Custom/Paid API (OpenAI-compatible)
    custom_provider?: string;
    custom_base_url?: string;
    custom_key?: string;
    custom_model?: string;

    // Search APIs
    brave_key?: string;
    serper_key?: string;
    jina_key?: string;

    // Literature APIs
    elsevier_key?: string;
    semantic_scholar_key?: string; // S2 API key for higher rate limits
    pubmed_email?: string;

    // SurfSense Knowledge Engine
    surfsense_url?: string;
    surfsense_key?: string;
    surfsense_auto_start?: boolean;

    // Bohrium Swarm Intelligence (MCP)
    bohrium_url?: string;
  };
  // New V2 Schema Additions
  pharma: {
    enable_pubtator: boolean;
    enable_semantic_scholar: boolean;
    enable_unpaywall: boolean;
    citation_threshold: 'low' | 'medium' | 'high';
    sources: {
      pubmed: boolean;
      pmc: boolean;
      biorxiv: boolean;
      chemrxiv: boolean;
      clinicaltrials: boolean;
      google_scholar: boolean;
      openalex: boolean;
      semantic_scholar: boolean;
      ieee: boolean;
      elsevier: boolean;
      scopus: boolean;
      wos: boolean;
      science_index: boolean;
    };
  };
  ai_advanced: {
    context_window: number;
    gpu_layers: number;
    thread_count: number;
    // Add missing optional settings to prevent build errors if referenced elsewhere
    provider?: string;
    endpoint?: string;
    key?: string;
    performance_profile?: string; // "high", "moderate", "low"
  };
  persona: {
    name?: string;
    email?: string;
    organization?: string;
    department?: string;
    roles: UserRole[];
    strictness: 'exploratory' | 'balanced' | 'conservative';
    introduction: string;
    research_focus: string;
    bot_name?: string;
    bot_instructions?: string;
  };
  output: {
    format: 'markdown' | 'pdf' | 'docx' | 'latex';
    citation_style: 'apa' | 'nature' | 'ieee' | 'chicago';
    include_disclosure: boolean;
    output_dir: string;
  };
  system: {
    max_cpu_percent: number;
    internet_research?: boolean; // Agent Zero V2
    auto_update?: boolean;
    log_level?: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  };
}

export interface ConnectionTest {
  type: 'llm' | 'database' | 'elsevier' | 'bohrium' | 'brave';
  status: 'success' | 'error' | 'warning';
  message: string;
  success?: boolean; // For compatibility
}


export interface SystemInfo {
  os: string;
  cpu_cores: number;
  ram_total_gb: number;
  ram_available_gb: number;
  disk_free_gb: number;
  temp_writable: boolean;
  python_version: string;
}

// Helper function for API calls
async function apiRequest<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;

  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 60000); // 60s timeout

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });

    clearTimeout(id);

    if (!response.ok) {
      let message = 'API request failed';
      try {
        const error = await response.json();
        message = error.message || error.detail || message;
      } catch {
        // Fallback for non-JSON or missing message
      }
      throw new Error(message);
    }

    return response.json();
  } catch (error: any) {
    if (error.name === 'AbortError') {
      throw new Error('Request timed out after 60 seconds');
    }
    throw error;
  } finally {
    clearTimeout(id);
  }
}

export const api = {
  // Research endpoints
  startResearch: (topic: string, mode: 'search' | 'synthesize' | 'write' = 'synthesize', taskId?: string) =>
    apiRequest<{ taskId: string, status: string, result: string, provider: string }>('/research/start', {
      method: 'POST',
      body: JSON.stringify({ topic, mode, taskId }),
    }),

  getStatus: (taskId: string) =>
    apiRequest<ResearchStatus>(`/research/status/${taskId}`),


  getResults: (taskId: string) =>
    apiRequest<ResearchResults>(`/research/${taskId}/results`),

  agentChat: (message: string) =>
    apiRequest<{ reply: string; provider: string; enhanced?: boolean }>('/agent/chat', {
      method: 'POST',
      body: JSON.stringify({ message })
    }),

  // Agent Zero universal execute - invoke any software function
  agentExecute: (action: string, params: Record<string, any> = {}) =>
    apiRequest<{ status: string; action: string; results?: any; error?: string }>('/agent/execute', {
      method: 'POST',
      body: JSON.stringify({ action, params })
    }),

  cancelResearch: (taskId: string) =>
    apiRequest<{ success: boolean }>(`/research/${taskId}/cancel`, {
      method: 'POST',
    }),

  // Lab interface endpoints
  generateProtocol: (request: ProtocolRequest) =>
    apiRequest<{ url: string; filename: string }>('/lab/protocol', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  generateReport: (request: ReportRequest) =>
    apiRequest<{ url: string; filename: string }>('/lab/report', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  getRecentExports: () =>
    apiRequest<{ id: string; type: string; filename: string; createdAt: string }[]>('/lab/exports'),

  // Agent Zero System Diagnosis
  diagnoseOllama: () =>
    apiRequest<{ success: boolean; message: string }>('/diagnose/ollama', {
      method: 'POST'
    }),

  exportResult: (format: 'pdf' | 'docx' | 'xlsx', data: any) =>
    apiRequest<{ path: string }>('/export', {
      method: 'POST',
      body: JSON.stringify({ format, data }),
    }),

  checkCompliance: (text: string) =>
    apiRequest<{ compliant: boolean, scores: any, issues: any[] }>('/compliance/check', {
      method: 'POST',
      body: JSON.stringify({ text })
    }),

  // Settings endpoints
  testConnection: (config: any) =>
    apiRequest<ConnectionTest>('/settings/test', {
      method: 'POST',
      body: JSON.stringify(config)
    }),



  checkNeo4j: (uri: string, user: string, password: string) =>
    apiRequest<{ status: string; message: string }>('/settings/neo4j/check', {
      method: 'POST',
      body: JSON.stringify({ uri, user, password })
    }),

  getSettings: () =>
    apiRequest<Settings>('/settings'),

  saveSettings: (settings: Settings) =>
    apiRequest<{ success: boolean }>('/settings', {
      method: 'POST',
      body: JSON.stringify(settings),
    }),

  resetSettings: () =>
    apiRequest<{ success: boolean; config: Settings }>('/settings/reset', {
      method: 'POST',
    }),

  getSystemInfo: () =>
    apiRequest<SystemInfo>('/system/info'),

  // History endpoints
  getResearchHistory: () =>
    apiRequest<{ id: string; topic: string; status: string; createdAt: string }[]>('/research/history'),

  // Digital Library Endpoints (Phase 5)
  uploadFile: (formData: FormData) =>
    apiRequest<{ status: string; file: any }>('/library/upload', {
      method: 'POST',
      body: formData,
      // Note: No Content-Type header needed for FormData; browser sets boundary
      headers: {}
    }),

  getLibraryFiles: () =>
    apiRequest<{ id: string; filename: string; size_bytes: number; added_at: string; processed: boolean; metadata: any }[]>('/library/files'),

  deleteLibraryFile: (fileId: string) =>
    apiRequest<{ status: string }>(`/library/files/${fileId}`, {
      method: 'DELETE',
    }),

  // Convenience methods for KnowledgeBaseView
  listLibraryFiles: () =>
    apiRequest<{ id: string; filename: string; size_bytes: number; added_at: string; processed: boolean; metadata: any }[]>('/library/files'),

  uploadLibraryFile: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return apiRequest<{ status: string; file: any }>('/library/upload', {
      method: 'POST',
      body: formData,
      headers: {}
    });
  },

  queryLibrary: (query: string, topK: number = 5) =>
    apiRequest<{ text: string; score: number; metadata: any }[]>('/library/search', {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    }),

  // Publication Endpoints (Phase 3)
  exportToLatex: (request: { title: string; author: string; affiliation: string; abstract: string; content_markdown: string }) =>
    apiRequest<{ latex_source: string }>('/publication/export/latex', {
      method: 'POST',
      body: JSON.stringify(request),
    }),

  registerFigure: (figure: { title: string; caption: string; code: string; path: string }) =>
    apiRequest<{ figure_id: string }>('/publication/figures', {
      method: 'POST',
      body: JSON.stringify(figure),
    }),

  // Statistics (Phase 4)
  analyzeStatistics: (data: any[], design: string, tier: string) =>
    apiRequest<any>('/statistics/analyze', {
      method: 'POST',
      body: JSON.stringify({ data, design, tier }),
    }),

  // Journal Intelligence (Phase 5)
  verifyJournal: (data: { title: string; issn: string; url?: string }) =>
    apiRequest<any>('/journal/verify', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // OmniTools Native (Phase 14)
  tools: {
    mergePDFs: async (formData: FormData) => {
      const response = await fetch(`${API_BASE}/tools/pdf/merge`, {
        method: 'POST',
        body: formData
      });
      if (!response.ok) throw new Error('Merge failed');
      return response.blob();
    },
    convertImage: async (formData: FormData) => {
      const response = await fetch(`${API_BASE}/tools/image/convert`, {
        method: 'POST',
        body: formData
      });
      if (!response.ok) throw new Error('Conversion failed');
      return response.blob();
    },
    processData: async (formData: FormData) => {
      const response = await fetch(`${API_BASE}/tools/data/process`, {
        method: 'POST',
        body: formData
      });
      if (!response.ok) throw new Error('Data processing failed');
      return response.blob();
    }
  },

  // PhD Thesis Core (Phase 7)
  thesis: {
    getStructure: () =>
      apiRequest<Record<string, any>>('/thesis/structure'),

    validateChapter: (chapterId: string) =>
      apiRequest<{ status: string, message?: string, missing_items?: string[] }>(`/thesis/validate/${chapterId}`),

    generateChapter: (chapterId: string, topic: string) =>
      apiRequest<{ status: string, content?: string, reason?: string, details?: any }>('/thesis/generate', {
        method: 'POST',
        body: JSON.stringify({ chapter_id: chapterId, topic })
      })
  },
  literature: {
    verifyCitations: (text: string) =>
      apiRequest<{ integrity_score: number, total_citations: number, valid_count: number, suspicious_count: number, unverified_count: number, details: any[] }>('/literature/verify', {
        method: 'POST',
        body: JSON.stringify({ text })
      })
  },
  // Google Drive Backup (Phase 10)
  backup: {
    getAuthUrl: () =>
      apiRequest<{ url: string }>('/backup/auth/url', { method: 'POST' }),

    verifyAuth: (code: string) =>
      apiRequest<{ status: string; user: any }>('/backup/auth/verify', {
        method: 'POST',
        body: JSON.stringify({ code })
      }),

    getStatus: () =>
      apiRequest<{ email?: string; name?: string; connected: boolean }>('/backup/status'),

    runBackup: () =>
      apiRequest<{ status: string; message: string }>('/backup/run', { method: 'POST' }),

    getHistory: () =>
      apiRequest<{ id: string; name: string; created_time: string; size: number }[]>('/backup/history'),

    restore: (snapshotId: string) =>
      apiRequest<{ status: string; message: string }>('/backup/restore', {
        method: 'POST',
        body: JSON.stringify({ snapshot_id: snapshotId })
      })
  },

  // Knowledge Base & Podcast (Phase 33)
  knowledge: {
    query: (query: string, topK: number = 5) =>
      apiRequest<{ status: string; query: string; results: any[] }>('/knowledge/query', {
        method: 'POST',
        body: JSON.stringify({ query, top_k: topK })
      }),

    generatePodcast: (text: string, voice: string = 'alloy') =>
      apiRequest<{ status: string; audio_format?: string; audio_base64?: string; error?: string }>('/knowledge/podcast', {
        method: 'POST',
        body: JSON.stringify({ text, voice })
      })
  },

  // Slides Generation (Phase 35)
  slides: {
    generate: (params: {
      source: 'knowledge_base' | 'search' | 'prompt' | 'documents';
      topic?: string;
      searchQuery?: string;
      customPrompt?: string;
      documentIds?: string[];
      style?: string;
      numSlides?: number;
      includeCitations?: boolean;
    }) =>
      apiRequest<{
        status: string;
        slides: Array<{
          index: number;
          type: string;
          title: string;
          content: string;
          style: any;
        }>;
        num_slides: number;
        generated_at: string;
      }>('/slides/generate', {
        method: 'POST',
        body: JSON.stringify({
          source: params.source,
          topic: params.topic || '',
          search_query: params.searchQuery || '',
          custom_prompt: params.customPrompt || '',
          document_ids: params.documentIds || [],
          style: params.style || 'academic',
          num_slides: params.numSlides || 10,
          include_citations: params.includeCitations ?? true
        })
      }),

    getStyles: () =>
      apiRequest<{
        styles: Array<{ id: string; name: string; description: string }>;
      }>('/slides/styles'),

    render: (slides: any[], style: string, title: string) =>
      apiRequest<{ status: string; html: string }>('/slides/render', {
        method: 'POST',
        body: JSON.stringify({ slides, style, title })
      })
  },

  // Auth & Licensing
  auth: {
    verify: (name: string, email: string) =>
      apiRequest<{ success: boolean; message: string; user?: any }>('/auth/verify', {
        method: 'POST',
        body: JSON.stringify({ name, email })
      })
  },

  // Enhanced Project System (Phase 11)
  projects: {
    list: (type?: string) =>
      apiRequest<Project[]>(`/enhanced/projects${type ? `?project_type=${type}` : ''}`),

    create: (title: string, type: string, context?: string) =>
      apiRequest<Project>(`/enhanced/project?project_title=${encodeURIComponent(title)}&project_type=${encodeURIComponent(type)}${context ? `&additional_context=${encodeURIComponent(context)}` : ''}`, {
        method: 'POST'
      }),

    getStatus: (projectId: string) =>
      apiRequest<Project>(`/enhanced/project/${projectId}`),

    getSystemStatus: () =>
      apiRequest<EnhancedSystemStatus>('/enhanced/system/status')
},

  // Statistics Export (Phase 14)
  statistics: {
    export: async (
      analysisId: string,
      format: 'json' | 'csv' | 'latex' | 'markdown',
      includeAssumptions: boolean = true,
      includeInterpretation: boolean = true,
      includeCode: boolean = false
    ) =>
      apiRequest<{ success: boolean; output_path?: string; error?: string }>('/api/statistics/export', {
        method: 'POST',
        body: JSON.stringify({
          analysis_id: analysisId,
          format: format,
          include_assumptions: includeAssumptions,
          include_interpretation: includeInterpretation,
          include_code: includeCode
        })
      })
  }
};

export default api;