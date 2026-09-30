import {
  AIEmployee,
  ApiError,
  AuthResponse,
  ChatResponse,
  Company,
  Conversation,
  DocumentChunkItem,
  DocumentItem,
  DocumentStatusResponse,
  DocumentUploadResponse,
  EvaluationBaseline,
  EvaluationResultItem,
  EvaluationRun,
  KnowledgeBase,
  Membership,
  Message,
  User,
} from '@/types';

const getApiBaseUrl = (): string => {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!envUrl || envUrl.includes(':8001')) {
    return 'http://localhost:8000/api/v1';
  }
  return envUrl;
};

const API_BASE_URL = getApiBaseUrl();

class ApiClient {
  private getAuthToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('access_token');
  }

  private getActiveCompanyId(): string | null {
    if (typeof window === 'undefined') return null;
    const cid = localStorage.getItem('active_company_id');
    if (!cid || cid === 'undefined' || cid === 'null' || cid.trim() === '') return null;
    return cid.trim();
  }

  public setSession(token: string, companyId?: string): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem('access_token', token);
    if (companyId) {
      localStorage.setItem('active_company_id', companyId);
    }
  }

  public clearSession(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem('access_token');
    localStorage.removeItem('active_company_id');
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const token = this.getAuthToken();
    const activeCompanyId = this.getActiveCompanyId();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
      ...((options.headers as Record<string, string>) || {}),
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (activeCompanyId) {
      headers['X-Company-ID'] = activeCompanyId;
    }

    const response = await fetch(url, {
      ...options,
      headers,
    });

    if (response.status === 204) {
      return {} as T;
    }

    let data: any;
    try {
      data = await response.json();
    } catch {
      data = null;
    }

    if (!response.ok) {
      const errMsg =
        data?.error?.message ||
        (Array.isArray(data?.error?.details)
          ? data.error.details.map((d: any) => d.message || d.msg).join(', ')
          : null) ||
        (typeof data?.detail === 'string' ? data.detail : null) ||
        (typeof data === 'string' ? data : null) ||
        `Request failed with status ${response.status}: ${response.statusText || 'Unknown error'}`;
      throw new Error(errMsg);
    }

    return data as T;
  }

  // Auth Endpoints
  async signup(payload: { email: string; password: string; full_name: string; company_name?: string }): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    this.setSession(res.token.access_token, res.company?.id);
    return res;
  }

  async login(payload: { email: string; password: string }): Promise<AuthResponse> {
    const res = await this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
    this.setSession(res.token.access_token);
    return res;
  }

  async getMe(): Promise<{ user: User; companies: { membership_id: string; role: string; company: Company }[] }> {
    return this.request('/auth/me');
  }

  // Companies Endpoints
  async getCompanies(): Promise<Membership[]> {
    return this.request<Membership[]>('/companies/');
  }

  async createCompany(payload: { name: string; slug?: string }): Promise<Company> {
    return this.request<Company>('/companies/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // AI Employees Endpoints (Tenant-Scoped)
  async getAIEmployees(): Promise<AIEmployee[]> {
    return this.request<AIEmployee[]>('/ai-employees/');
  }

  async getAIEmployee(id: string): Promise<AIEmployee> {
    return this.request<AIEmployee>(`/ai-employees/${id}`);
  }

  async createAIEmployee(payload: Partial<AIEmployee>): Promise<AIEmployee> {
    return this.request<AIEmployee>('/ai-employees/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateAIEmployee(id: string, payload: Partial<AIEmployee>): Promise<AIEmployee> {
    return this.request<AIEmployee>(`/ai-employees/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  async deleteAIEmployee(id: string): Promise<void> {
    return this.request<void>(`/ai-employees/${id}`, {
      method: 'DELETE',
    });
  }

  async assignEmployeeKnowledgeBases(employeeId: string, knowledgeBaseIds: string[]): Promise<AIEmployee> {
    return this.request<AIEmployee>(`/ai-employees/${employeeId}/knowledge-bases`, {
      method: 'PUT',
      body: JSON.stringify({ knowledge_base_ids: knowledgeBaseIds }),
    });
  }

  async getEmployeeKnowledgeBases(employeeId: string): Promise<KnowledgeBase[]> {
    return this.request<KnowledgeBase[]>(`/ai-employees/${employeeId}/knowledge-bases`);
  }

  // Phase 4: Public Runtime & Widget Embed Endpoints
  async publishAIEmployee(
    id: string,
    payload?: import('@/types').EmployeePublishRequest
  ): Promise<AIEmployee> {
    return this.request<AIEmployee>(`/ai-employees/${id}/publish`, {
      method: 'POST',
      body: JSON.stringify(payload || { is_published: true, allowed_domains: [] }),
    });
  }

  async unpublishAIEmployee(id: string): Promise<AIEmployee> {
    return this.request<AIEmployee>(`/ai-employees/${id}/unpublish`, {
      method: 'POST',
    });
  }

  async getAIEmployeeEmbed(id: string): Promise<import('@/types').EmployeeEmbedCodeResponse> {
    return this.request<import('@/types').EmployeeEmbedCodeResponse>(`/ai-employees/${id}/embed`);
  }

  async updateAIEmployeeWidgetConfig(
    id: string,
    config: import('@/types').EmployeeWidgetConfigRequest
  ): Promise<AIEmployee> {
    return this.request<AIEmployee>(`/ai-employees/${id}/widget-config`, {
      method: 'PUT',
      body: JSON.stringify(config),
    });
  }

  async getPublicEmployeeConfig(publicId: string): Promise<import('@/types').PublicEmployeeConfig> {
    return this.request<import('@/types').PublicEmployeeConfig>(`/public/employees/${publicId}/config`);
  }

  // Voice Endpoints (Phase 5)
  async getAvailableVoices(): Promise<import('@/types').AvailableVoicesResponse> {
    return this.request<import('@/types').AvailableVoicesResponse>('/voice/voices');
  }


  // Knowledge Base Endpoints (Tenant-Scoped)
  async getKnowledgeBases(): Promise<KnowledgeBase[]> {
    return this.request<KnowledgeBase[]>('/knowledge-bases/');
  }

  async getKnowledgeBase(id: string): Promise<KnowledgeBase> {
    return this.request<KnowledgeBase>(`/knowledge-bases/${id}`);
  }

  async createKnowledgeBase(payload: { name: string; description?: string }): Promise<KnowledgeBase> {
    return this.request<KnowledgeBase>('/knowledge-bases/', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async updateKnowledgeBase(id: string, payload: { name?: string; description?: string; status?: string }): Promise<KnowledgeBase> {
    return this.request<KnowledgeBase>(`/knowledge-bases/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  async deleteKnowledgeBase(id: string): Promise<void> {
    return this.request<void>(`/knowledge-bases/${id}`, {
      method: 'DELETE',
    });
  }

  // Document Endpoints (Tenant-Scoped)
  async getDocuments(kbId: string): Promise<DocumentItem[]> {
    return this.request<DocumentItem[]>(`/knowledge-bases/${kbId}/documents`);
  }

  async uploadDocument(kbId: string, file: File): Promise<DocumentUploadResponse> {
    const url = `${API_BASE_URL}/knowledge-bases/${kbId}/documents`;
    const token = this.getAuthToken();
    const activeCompanyId = this.getActiveCompanyId();

    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (activeCompanyId) headers['X-Company-ID'] = activeCompanyId;

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    });

    const data = await response.json();
    if (!response.ok) {
      const err: ApiError = data;
      throw new Error(err.error?.message || 'File upload failed');
    }
    return data as DocumentUploadResponse;
  }

  async getDocumentStatus(docId: string): Promise<DocumentStatusResponse> {
    return this.request<DocumentStatusResponse>(`/documents/${docId}/status`);
  }

  async retryDocumentIngestion(docId: string): Promise<DocumentUploadResponse> {
    return this.request<DocumentUploadResponse>(`/documents/${docId}/retry`, {
      method: 'POST',
    });
  }

  async cancelDocumentIngestion(docId: string): Promise<DocumentStatusResponse> {
    return this.request<DocumentStatusResponse>(`/documents/${docId}/cancel`, {
      method: 'POST',
    });
  }

  async getDocument(docId: string): Promise<DocumentItem> {
    return this.request<DocumentItem>(`/documents/${docId}`);
  }

  async getDocumentChunks(docId: string): Promise<DocumentChunkItem[]> {
    return this.request<DocumentChunkItem[]>(`/documents/${docId}/chunks`);
  }

  async deleteDocument(docId: string): Promise<void> {
    return this.request<void>(`/documents/${docId}`, {
      method: 'DELETE',
    });
  }

  // Conversation & Chat Endpoints (Tenant-Scoped)
  async createConversation(aiEmployeeId: string, title?: string): Promise<Conversation> {
    return this.request<Conversation>('/conversations/', {
      method: 'POST',
      body: JSON.stringify({
        ai_employee_id: aiEmployeeId,
        title: title || undefined,
      }),
    });
  }

  async listConversations(aiEmployeeId?: string): Promise<Conversation[]> {
    const query = aiEmployeeId ? `?ai_employee_id=${aiEmployeeId}` : '';
    return this.request<Conversation[]>(`/conversations/${query}`);
  }

  async getConversation(id: string): Promise<Conversation> {
    return this.request<Conversation>(`/conversations/${id}`);
  }

  async deleteConversation(id: string): Promise<void> {
    return this.request<void>(`/conversations/${id}`, {
      method: 'DELETE',
    });
  }

  async getMessages(conversationId: string): Promise<Message[]> {
    return this.request<Message[]>(`/conversations/${conversationId}/messages`);
  }

  async sendMessage(
    conversationId: string,
    content: string,
    pendingActionId?: string,
    confirmAction?: boolean
  ): Promise<ChatResponse> {
    return this.request<ChatResponse>(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({
        content,
        pending_action_id: pendingActionId || undefined,
        confirm_action: confirmAction !== undefined ? confirmAction : false,
      }),
    });
  }

  // Phase 3: Tool & Agent Endpoints
  async getTools(): Promise<import('@/types').ToolDefinition[]> {
    return this.request<import('@/types').ToolDefinition[]>('/tools');
  }

  async getEmployeeTools(employeeId: string): Promise<import('@/types').AIEmployeeTool[]> {
    return this.request<import('@/types').AIEmployeeTool[]>(`/tools/employees/${employeeId}`);
  }

  async assignEmployeeTools(employeeId: string, toolNames: string[]): Promise<import('@/types').AIEmployeeTool[]> {
    return this.request<import('@/types').AIEmployeeTool[]>(`/tools/employees/${employeeId}`, {
      method: 'PUT',
      body: JSON.stringify({ tool_names: toolNames }),
    });
  }

  async confirmPendingAction(actionId: string, confirm: boolean): Promise<any> {
    return this.request<any>(`/business-data/pending-actions/${actionId}/confirm`, {
      method: 'POST',
      body: JSON.stringify({ confirm }),
    });
  }

  // Phase 8: RAG Evaluation & Benchmarking
  async getEvaluationRuns(): Promise<EvaluationRun[]> {
    return this.request<EvaluationRun[]>('/evaluations');
  }

  async getEvaluationRun(id: string): Promise<EvaluationRun> {
    return this.request<EvaluationRun>(`/evaluations/${id}`);
  }

  async getEvaluationReport(id: string): Promise<string> {
    const url = `${API_BASE_URL}/evaluations/${id}/report`;
    const token = this.getAuthToken();
    const activeCompanyId = this.getActiveCompanyId();
    const headers: Record<string, string> = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (activeCompanyId) headers['X-Company-ID'] = activeCompanyId;

    const res = await fetch(url, { headers });
    if (!res.ok) throw new Error('Failed to fetch markdown report');
    return res.text();
  }

  async getEvaluationBaseline(): Promise<EvaluationBaseline | null> {
    return this.request<EvaluationBaseline | null>('/evaluations/baseline');
  }

  async runEvaluation(payload: {
    ai_employee_id: string;
    dataset_name?: string;
    run_generation_eval?: boolean;
    custom_dataset?: any[];
  }): Promise<EvaluationRun> {
    return this.request<EvaluationRun>('/evaluations/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async setEvaluationBaseline(id: string): Promise<any> {
    return this.request<any>(`/evaluations/${id}/set-baseline`, {
      method: 'POST',
    });
  }

  // Phase 11: Production Observability & Distributed Tracing
  async listTraces(params?: { ai_employee_id?: string; limit?: number; offset?: number }): Promise<any[]> {
    const q = new URLSearchParams();
    if (params?.ai_employee_id) q.append('ai_employee_id', params.ai_employee_id);
    if (params?.limit) q.append('limit', params.limit.toString());
    if (params?.offset) q.append('offset', params.offset.toString());
    const query = q.toString() ? `?${q.toString()}` : '';
    return this.request<any[]>(`/observability/traces${query}`);
  }

  async getTrace(traceId: string): Promise<any> {
    return this.request<any>(`/observability/traces/${traceId}`);
  }

  async getMetricsSummary(): Promise<any> {
    return this.request<any>('/observability/metrics/summary');
  }

  async listAuditLogs(params?: { event_type?: string; limit?: number; offset?: number }): Promise<any[]> {
    const q = new URLSearchParams();
    if (params?.event_type) q.append('event_type', params.event_type);
    if (params?.limit) q.append('limit', params.limit.toString());
    if (params?.offset) q.append('offset', params.offset.toString());
    const query = q.toString() ? `?${q.toString()}` : '';
    return this.request<any[]>(`/observability/audit-logs${query}`);
  }

  // Phase 12: AI Employee Playground
  async createPlaygroundSession(payload: {
    ai_employee_id: string;
    session_name?: string;
    config_overrides?: any;
  }): Promise<any> {
    return this.request<any>('/playground/sessions', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async listPlaygroundSessions(aiEmployeeId?: string): Promise<any[]> {
    const q = aiEmployeeId ? `?ai_employee_id=${aiEmployeeId}` : '';
    return this.request<any[]>(`/playground/sessions${q}`);
  }

  async getPlaygroundSession(sessionId: string): Promise<any> {
    return this.request<any>(`/playground/sessions/${sessionId}`);
  }

  async sendPlaygroundMessage(sessionId: string, content: string): Promise<any> {
    return this.request<any>(`/playground/sessions/${sessionId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    });
  }

  async deletePlaygroundSession(sessionId: string): Promise<void> {
    return this.request<void>(`/playground/sessions/${sessionId}`, {
      method: 'DELETE',
    });
  }

  async compareConfigurations(payload: {
    ai_employee_id: string;
    test_queries: string[];
    config_a: any;
    config_b: any;
  }): Promise<any> {
    return this.request<any>('/playground/compare', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // Phase 13: Tenant Cost Metering & Budgets
  async getUsageSummary(aiEmployeeId?: string, days: number = 30): Promise<any> {
    const q = new URLSearchParams();
    if (aiEmployeeId) q.append('ai_employee_id', aiEmployeeId);
    q.append('days', days.toString());
    return this.request<any>(`/usage/summary?${q.toString()}`);
  }

  async listUsageLedger(aiEmployeeId?: string, limit: number = 50): Promise<any[]> {
    const q = new URLSearchParams();
    if (aiEmployeeId) q.append('ai_employee_id', aiEmployeeId);
    q.append('limit', limit.toString());
    return this.request<any[]>(`/usage/ledger?${q.toString()}`);
  }

  async listBudgets(): Promise<any[]> {
    return this.request<any[]>('/budgets');
  }

  async createBudget(payload: {
    budget_name: string;
    limit_amount: number;
    period_type?: string;
    soft_limit_percent?: number;
    hard_limit_enabled?: boolean;
    ai_employee_id?: string;
  }): Promise<any> {
    return this.request<any>('/budgets', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async deleteBudget(id: string): Promise<void> {
    return this.request<void>(`/budgets/${id}`, {
      method: 'DELETE',
    });
  }
}

export const api = new ApiClient();

