import { apiClient } from './client';
import { ChatResponse, ChatConversation } from '../types';

const CHATBOT_API_KEY =
  import.meta.env.VITE_CHATBOT_API_KEY || '';

const chatHeaders: Record<string, string> = CHATBOT_API_KEY
  ? { 'X-Chatbot-API-Key': CHATBOT_API_KEY }
  : {};

export const chatApi = {
  /**
   * Send a message to the AI Assistant via Chatbot API Key.
   */
  async sendMessage(content: string, conversationId?: string): Promise<ChatResponse> {
    const res = await apiClient.post<ChatResponse>(
      '/chat/message',
      {
        content,
        conversation_id: conversationId || undefined,
      },
      { headers: chatHeaders }
    );
    return res.data;
  },

  /**
   * List conversations for the authenticated user.
   */
  async listConversations(): Promise<ChatConversation[]> {
    const res = await apiClient.get<ChatConversation[]>('/chat/conversations', {
      headers: chatHeaders,
    });
    return res.data;
  },

  /**
   * Get full conversation history.
   */
  async getConversation(conversationId: string): Promise<ChatConversation> {
    const res = await apiClient.get<ChatConversation>(`/chat/conversations/${conversationId}`, {
      headers: chatHeaders,
    });
    return res.data;
  },

  /**
   * Delete a conversation.
   */
  async deleteConversation(conversationId: string): Promise<void> {
    await apiClient.delete(`/chat/conversations/${conversationId}`, {
      headers: chatHeaders,
    });
  },
};

