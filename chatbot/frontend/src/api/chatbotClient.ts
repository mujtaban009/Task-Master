// Type declaration for import.meta.env across all TypeScript configurations
interface CustomImportMeta {
  env?: {
    VITE_CHATBOT_API_URL?: string;
    VITE_CHATBOT_API_KEY?: string;
  };
}

// Chatbot dedicated microservice configuration
export const CHATBOT_API_KEY: string =
  ((import.meta as unknown as CustomImportMeta)?.env?.VITE_CHATBOT_API_KEY) ||
  '';

export const CHATBOT_BASE_URL: string =
  ((import.meta as unknown as CustomImportMeta)?.env?.VITE_CHATBOT_API_URL) ||
  'http://127.0.0.1:8001/api/chat';

export interface ChatMessage {
  id: string;
  conversation_id: string;
  sender: 'user' | 'assistant';
  content: string;
  metadata_?: Record<string, any>;
  created_at: string;
}

export interface ChatConversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
}

export interface ChatResponse {
  conversation_id: string;
  user_message: ChatMessage;
  assistant_message: ChatMessage;
  tools_executed?: string[];
}

/**
 * Lightweight, zero-dependency HTTP client for the Chatbot Microservice.
 * Built with native Fetch API for universal compatibility without external dependencies.
 */
async function fetchClient<T>(
  endpoint: string,
  options: {
    method?: string;
    body?: any;
    headers?: Record<string, string>;
  } = {}
): Promise<{ data: T }> {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('access_token') : null;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(CHATBOT_API_KEY ? { 'X-Chatbot-API-Key': CHATBOT_API_KEY } : {}),
    ...(options.headers || {}),
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const base = CHATBOT_BASE_URL.replace(/\/+$/, '');
  const path = endpoint.replace(/^\/+/, '');
  const url = `${base}/${path}`;

  const response = await fetch(url, {
    method: options.method || 'GET',
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Chatbot API Error (${response.status}): ${errorText}`);
  }

  if (response.status === 204) {
    return { data: undefined as unknown as T };
  }

  const data = (await response.json()) as T;
  return { data };
}

export const chatbotApiClient = {
  get: <T = any>(endpoint: string) => fetchClient<T>(endpoint, { method: 'GET' }),
  post: <T = any>(endpoint: string, body?: any) => fetchClient<T>(endpoint, { method: 'POST', body }),
  delete: <T = any>(endpoint: string) => fetchClient<T>(endpoint, { method: 'DELETE' }),
};

export const chatbotService = {
  async sendMessage(content: string, conversationId?: string): Promise<ChatResponse> {
    const res = await chatbotApiClient.post<ChatResponse>('/chat/message', {
      content,
      conversation_id: conversationId || null,
    });
    return res.data;
  },

  async listConversations(): Promise<ChatConversation[]> {
    const res = await chatbotApiClient.get<ChatConversation[]>('/chat/conversations');
    return res.data;
  },

  async getConversation(id: string): Promise<ChatConversation> {
    const res = await chatbotApiClient.get<ChatConversation>(`/chat/conversations/${id}`);
    return res.data;
  },

  async deleteConversation(id: string): Promise<void> {
    await chatbotApiClient.delete(`/chat/conversations/${id}`);
  },

  async checkHealth(): Promise<any> {
    const res = await chatbotApiClient.get('/health');
    return res.data;
  },
};
