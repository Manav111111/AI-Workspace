export type MembershipRole = 'OWNER' | 'ADMIN' | 'MEMBER';

export type AIEmployeeStatus = 'DRAFT' | 'ACTIVE' | 'INACTIVE';

export type KnowledgeBaseStatus = 'ACTIVE' | 'INACTIVE';

export type DocumentStatus = 'UPLOADED' | 'PROCESSING' | 'PROCESSED' | 'FAILED' | 'DELETED';

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface Company {
  id: string;
  name: string;
  slug: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Membership {
  id: string;
  user_id: string;
  company_id: string;
  role: MembershipRole;
  created_at: string;
  company?: Company;
}

export interface AIEmployee {
  id: string;
  company_id: string;
  name: string;
  role: string;
  description?: string | null;
  personality?: string | null;
  system_prompt?: string | null;
  language: string;
  status: AIEmployeeStatus;
  avatar_config: Record<string, any>;
  voice_config: Record<string, any>;
  created_at: string;
  updated_at: string;
  knowledge_base_ids?: string[];
  assigned_knowledge_bases?: KnowledgeBase[];
  tool_names?: string[];
  tools?: string[];
  assigned_tools?: AIEmployeeTool[];
}

export interface KnowledgeBase {
  id: string;
  company_id: string;
  name: string;
  description?: string | null;
  status: KnowledgeBaseStatus;
  created_at: string;
  updated_at: string;
}

export interface DocumentItem {
  id: string;
  company_id: string;
  knowledge_base_id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  mime_type: string;
  file_size: number;
  status: DocumentStatus;
  error_message?: string | null;
  document_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunkItem {
  id: string;
  company_id: string;
  knowledge_base_id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  token_count: number;
  chunk_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface AuthResponse {
  user: User;
  company?: Company | null;
  token: {
    access_token: string;
    token_type: string;
  };
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: any;
  };
}

export interface Conversation {
  id: string;
  company_id: string;
  ai_employee_id: string;
  user_id?: string | null;
  title: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  chunk_id: string;
  document_id: string;
  document_name: string;
  page_number?: number | null;
  header_path?: string | null;
  score: number;
  preview?: string | null;
}

export interface ToolDefinition {
  name: string;
  description: string;
  permission: 'READ' | 'WRITE';
  input_schema: Record<string, any>;
}

export interface AIEmployeeTool {
  id: string;
  company_id?: string;
  ai_employee_id: string;
  tool_name: string;
  created_at: string;
}

export interface PendingToolAction {
  id: string;
  company_id: string;
  ai_employee_id: string;
  conversation_id: string;
  tool_name: string;
  validated_arguments: Record<string, any>;
  status: 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'EXPIRED';
  expires_at: string;
  created_at: string;
}

export interface PendingConfirmation {
  pending_action_id: string;
  tool_name: string;
  arguments: Record<string, any>;
  message?: string;
}

export interface Order {
  id: string;
  company_id: string;
  order_number: string;
  customer_identifier: string;
  status: string;
  items: Array<{ sku: string; name: string; qty: number; price: number }>;
  total: number;
  tracking_number?: string | null;
  created_at: string;
}

export interface Lead {
  id: string;
  company_id: string;
  name: string;
  email: string;
  phone?: string | null;
  interest?: string | null;
  source: string;
  status: string;
  created_at: string;
}

export interface SupportTicket {
  id: string;
  company_id: string;
  ticket_number: string;
  customer_email: string;
  subject: string;
  description: string;
  status: string;
  priority: string;
  created_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  company_id: string;
  role: 'USER' | 'ASSISTANT' | 'SYSTEM';
  content: string;
  citations: Citation[];
  message_metadata?: Record<string, any>;
  created_at: string;
}

export interface ChatResponse {
  user_message: Message;
  assistant_message: Message;
  citations: Citation[];
  tool_calls: Array<Record<string, any>>;
  pending_confirmation?: PendingConfirmation | null;
  metrics: Record<string, any>;
}
