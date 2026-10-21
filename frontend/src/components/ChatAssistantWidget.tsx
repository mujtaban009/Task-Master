import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../hooks/useAuth';
import { chatApi } from '../api/chat';
import { ChatMessage, ChatConversation } from '../types';
import {
  Bot,
  Sparkles,
  Send,
  Plus,
  History,
  Trash2,
  X,
  Minimize2,
  AlertCircle,
  ShieldCheck,
  User as UserIcon,
  Database,
  Loader2,
  CheckCircle2,
  Bell,
} from 'lucide-react';

export const ChatAssistantWidget: React.FC = () => {
  const { user, isAdmin } = useAuth();

  // Widget visibility state
  const [isOpen, setIsOpen] = useState<boolean>(() => {
    return sessionStorage.getItem('chat_widget_open') === 'true';
  });

  // Active conversation state
  const [conversationId, setConversationId] = useState<string | null>(() => {
    return sessionStorage.getItem('chat_active_conversation_id') || null;
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [conversations, setConversations] = useState<ChatConversation[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Role accent drives the 3D styles in index.css (violet = admin agent, emerald = user agent)
  const accentVars = (
    isAdmin
      ? {
          '--ai-accent': '#7c3aed',
          '--ai-accent-dark': '#4c1d95',
          '--ai-accent-soft': 'rgba(139, 92, 246, 0.45)',
          '--ai-accent-glow': 'rgba(124, 58, 237, 0.55)',
        }
      : {
          '--ai-accent': '#10b981',
          '--ai-accent-dark': '#047857',
          '--ai-accent-soft': 'rgba(16, 185, 129, 0.4)',
          '--ai-accent-glow': 'rgba(5, 150, 105, 0.5)',
        }
  ) as React.CSSProperties;

  // Subtle pointer tilt (max 2deg); disabled by prefers-reduced-motion in CSS
  const handleTilt = (e: React.MouseEvent<HTMLDivElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    e.currentTarget.style.setProperty('--ai-ry', `${((e.clientX - r.left) / r.width - 0.5) * 4}deg`);
    e.currentTarget.style.setProperty('--ai-rx', `${-((e.clientY - r.top) / r.height - 0.5) * 4}deg`);
  };
  const resetTilt = (e: React.MouseEvent<HTMLDivElement>) => {
    e.currentTarget.style.setProperty('--ai-ry', '0deg');
    e.currentTarget.style.setProperty('--ai-rx', '0deg');
  };

  // Sync open state to sessionStorage
  useEffect(() => {
    sessionStorage.setItem('chat_widget_open', isOpen ? 'true' : 'false');
  }, [isOpen]);

  // Sync conversation ID to sessionStorage
  useEffect(() => {
    if (conversationId) {
      sessionStorage.setItem('chat_active_conversation_id', conversationId);
    } else {
      sessionStorage.removeItem('chat_active_conversation_id');
    }
  }, [conversationId]);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    // Empty chat keeps the welcome screen at the top
    if (isOpen && messages.length > 0) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && !isHistoryOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen, isHistoryOpen]);

  // Load conversation messages on mount or conversationId change
  useEffect(() => {
    const fetchConversation = async () => {
      if (!conversationId) {
        setMessages([]);
        return;
      }
      try {
        const conv = await chatApi.getConversation(conversationId);
        if (conv.messages) {
          setMessages(conv.messages);
        }
      } catch (err: any) {
        console.error('Failed to load conversation:', err);
        // If 404 or invalid, reset conversation ID
        setConversationId(null);
        setMessages([]);
      }
    };

    fetchConversation();
  }, [conversationId]);

  // Load conversation list
  const loadConversationsList = async () => {
    setIsLoadingHistory(true);
    try {
      const list = await chatApi.listConversations();
      setConversations(list);
    } catch (err: any) {
      console.error('Failed to list conversations:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const handleToggleHistory = () => {
    const nextState = !isHistoryOpen;
    setIsHistoryOpen(nextState);
    if (nextState) {
      loadConversationsList();
    }
  };

  const handleSelectConversation = (id: string) => {
    setConversationId(id);
    setIsHistoryOpen(false);
    setError(null);
  };

  const handleNewChat = () => {
    setConversationId(null);
    setMessages([]);
    setIsHistoryOpen(false);
    setError(null);
    if (inputRef.current) {
      inputRef.current.focus();
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await chatApi.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (conversationId === id) {
        handleNewChat();
      }
    } catch (err: any) {
      console.error('Failed to delete conversation:', err);
    }
  };

  const handleSendMessage = async (customText?: string) => {
    const textToSend = (customText || inputMessage).trim();
    if (!textToSend || isLoading) return;

    setError(null);
    setInputMessage('');

    // Optimistically add the user message
    const tempUserMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      conversation_id: conversationId || '',
      sender: 'user',
      content: textToSend,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, tempUserMsg]);
    setIsLoading(true);

    try {
      const response = await chatApi.sendMessage(textToSend, conversationId || undefined);

      // Update current conversation ID if it was newly created
      if (!conversationId && response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      // Replace temp user message with real one and append assistant message
      setMessages((prev) => {
        const withoutTemp = prev.filter((m) => m.id !== tempUserMsg.id);
        return [...withoutTemp, response.user_message, response.assistant_message];
      });

      // Let task panels refetch when the agent changed tasks
      if (response.tools_executed?.some((t) => /create|assign|update/.test(t))) {
        window.dispatchEvent(new Event('tasks-changed'));
      }
    } catch (err: any) {
      console.error('Chat error:', err);
      const detail = err.response?.data?.detail || 'Unable to connect to AI Assistant. Please try again.';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Quick Action Chips: `fill` puts an editable example in the input instead of sending it
  const suggestions: { label: string; fill?: boolean }[] = isAdmin
    ? [
        { label: 'Add task Review weekly report to my tasks', fill: true },
        { label: 'Create task Update onboarding docs and assign it to alice@example.com', fill: true },
        { label: 'Pending tasks per user' },
        { label: 'Show all overdue tasks' },
      ]
    : [
        { label: 'Show all my tasks' },
        { label: 'Which tasks are still pending?' },
        { label: 'Add task Prepare meeting notes', fill: true },
        { label: 'Summarize my tasks' },
      ];

  const handleSuggestion = (s: { label: string; fill?: boolean }) => {
    if (s.fill) {
      setInputMessage(s.label);
      inputRef.current?.focus();
    } else {
      handleSendMessage(s.label);
    }
  };

  // Render pill badges for table cells
  const renderTableCell = (cellText: string, isHeader = false) => {
    const raw = cellText.replace(/^[*`]+|[*`]+$/g, '').trim().toLowerCase();

    if (!isHeader) {
      if (raw === 'high' || cellText.toLowerCase().includes('overdue')) {
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            {cellText.replace(/\*\*/g, '')}
          </span>
        );
      }
      if (raw === 'medium') {
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-amber-50 text-amber-700 border border-amber-200">
            Medium
          </span>
        );
      }
      if (raw === 'low') {
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
            Low
          </span>
        );
      }
      if (raw === 'completed') {
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
            Completed
          </span>
        );
      }
      if (raw === 'in_progress') {
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
            In Progress
          </span>
        );
      }
      if (raw === 'pending') {
        return (
          <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-yellow-50 text-yellow-800 border border-yellow-200">
            Pending
          </span>
        );
      }
    }

    return <span dangerouslySetInnerHTML={{ __html: formatInline(cellText) }} />;
  };

  // Helper to format AI message content with markdown tables, lists, headers
  const renderMessageContent = (content: string) => {
    const rawLines = content.split('\n');
    const blocks: { type: 'table' | 'line'; data: any }[] = [];

    let currentTableLines: string[] = [];

    const flushTable = () => {
      if (currentTableLines.length > 0) {
        const rows = currentTableLines.map((l) =>
          l.split('|').slice(1, -1).map((c) => c.trim())
        );
        const header = rows[0] || [];
        const body = rows.slice(1).filter((r) => !r.every((c) => /^:?-+:?$/.test(c)));
        blocks.push({
          type: 'table',
          data: { header, body },
        });
        currentTableLines = [];
      }
    };

    for (const line of rawLines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        currentTableLines.push(trimmed);
      } else {
        flushTable();
        blocks.push({ type: 'line', data: trimmed });
      }
    }
    flushTable();

    return (
      <div className="space-y-1.5 text-xs leading-relaxed">
        {blocks.map((block, bIdx) => {
          if (block.type === 'table') {
            const { header, body } = block.data;
            return (
              <div
                key={bIdx}
                className="overflow-x-auto my-2 rounded-lg border border-slate-200 bg-white shadow-sm max-w-full"
              >
                <table className="w-full text-left border-collapse text-[11px]">
                  <thead>
                    <tr className="bg-slate-100 text-slate-800 border-b border-slate-200 font-semibold">
                      {header.map((col: string, cIdx: number) => (
                        <th key={cIdx} className="py-2 px-2.5 whitespace-nowrap">
                          {renderTableCell(col, true)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {body.map((row: string[], rIdx: number) => (
                      <tr
                        key={rIdx}
                        className={
                          rIdx % 2 === 0
                            ? 'bg-white hover:bg-slate-50'
                            : 'bg-slate-50/60 hover:bg-slate-50'
                        }
                      >
                        {row.map((cell: string, cIdx: number) => (
                          <td key={cIdx} className="py-2 px-2.5 whitespace-nowrap text-slate-700">
                            {renderTableCell(cell, false)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          }

          const trimmed = block.data;

          // Empty line
          if (!trimmed) {
            return <div key={bIdx} className="h-1.5" />;
          }

          // Bullet point
          if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
            const bulletText = trimmed.replace(/^[-*•]\s+/, '');
            return (
              <div key={bIdx} className="flex items-start space-x-2 pl-2">
                <span className="text-slate-400 select-none">&bull;</span>
                <span dangerouslySetInnerHTML={{ __html: formatInline(bulletText) }} />
              </div>
            );
          }

          // Numbered list (e.g. "1. ")
          const matchNum = trimmed.match(/^(\d+)\.\s+(.+)$/);
          if (matchNum) {
            return (
              <div key={bIdx} className="flex items-start space-x-2 pl-2">
                <span className="font-semibold text-slate-600 text-[11px] min-w-[1.2rem] pt-0.5">
                  {matchNum[1]}.
                </span>
                <span dangerouslySetInnerHTML={{ __html: formatInline(matchNum[2]) }} />
              </div>
            );
          }

          // Header line (### or ## or ####)
          if (trimmed.startsWith('#### ')) {
            const headerText = trimmed.replace(/^#{4}\s+/, '');
            return (
              <div key={bIdx} className="font-semibold text-slate-700 pt-1.5 pb-0.5 text-[11px] uppercase tracking-wider">
                {headerText}
              </div>
            );
          }
          if (trimmed.startsWith('### ') || trimmed.startsWith('## ')) {
            const headerText = trimmed.replace(/^#{2,3}\s+/, '');
            return (
              <div key={bIdx} className="font-bold text-slate-900 pt-2 pb-0.5 text-xs uppercase tracking-wider">
                {headerText}
              </div>
            );
          }

          // Regular paragraph
          return (
            <p key={bIdx} dangerouslySetInnerHTML={{ __html: formatInline(trimmed) }} />
          );
        })}
      </div>
    );
  };

  // Format bold and code within text
  const formatInline = (text: string): string => {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-slate-900">$1</strong>')
      .replace(/\*([^*\s][^*]*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code class="bg-slate-100 text-slate-800 px-1 py-0.5 rounded text-xs font-mono">$1</code>');
  };

  const formatTime = (isoString?: string) => {
    if (!isoString) return '';
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50" style={accentVars}>
      {/* Floating Chat Panel */}
      {isOpen && (
        <div
          role="dialog"
          aria-label="AI Assistant Chat"
          onMouseMove={handleTilt}
          onMouseLeave={resetTilt}
          className="ai-panel fixed bottom-24 right-4 sm:right-6 w-[calc(100vw-2rem)] sm:w-[440px] h-[620px] max-h-[80vh] bg-white/95 backdrop-blur rounded-3xl border border-white/60 ring-1 ring-slate-900/5 flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="ai-header relative z-10 text-white px-4 py-3.5 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="ai-orb w-10 h-10 flex items-center justify-center text-white" aria-hidden="true">
                <Bot className="w-5 h-5 drop-shadow" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="font-semibold text-sm tracking-tight">
                    {isAdmin ? 'Admin Agent' : 'My Assistant'}
                  </h3>
                  {isAdmin ? (
                    <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-purple-500/20 text-purple-200 border border-purple-400/30">
                      <ShieldCheck className="w-2.5 h-2.5" />
                      <span>Admin RAG</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/20 text-emerald-200 border border-emerald-400/30">
                      <UserIcon className="w-2.5 h-2.5" />
                      <span>User RAG</span>
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-300">
                  {isAdmin ? 'Full database access · create & assign tasks' : 'Only your own tasks and details'}
                </p>
              </div>
            </div>

            {/* Header Actions */}
            <div className="flex items-center space-x-1 text-slate-300">
              <button
                onClick={handleToggleHistory}
                title="Conversation History"
                aria-label="Conversation history"
                aria-pressed={isHistoryOpen}
                className={`p-2 rounded-xl hover:text-white hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white/70 transition ${
                  isHistoryOpen ? 'bg-white/15 text-white' : ''
                }`}
              >
                <History className="w-4 h-4" />
              </button>
              <button
                onClick={handleNewChat}
                title="New Conversation"
                aria-label="New conversation"
                className="p-2 rounded-xl hover:text-white hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white/70 transition"
              >
                <Plus className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Close Assistant"
                aria-label="Close assistant"
                className="p-2 rounded-xl hover:text-white hover:bg-white/10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white/70 transition"
              >
                <Minimize2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Conversation History Drawer Overlay */}
          {isHistoryOpen ? (
            <div className="flex-1 flex flex-col bg-slate-50 overflow-hidden">
              <div className="px-4 py-2.5 border-b border-slate-200 flex items-center justify-between bg-white">
                <span className="text-xs font-semibold uppercase tracking-wider text-slate-600 flex items-center space-x-1.5">
                  <History className="w-3.5 h-3.5 text-slate-500" />
                  <span>Past Conversations</span>
                </span>
                <button
                  onClick={() => setIsHistoryOpen(false)}
                  className="text-xs text-slate-500 hover:text-slate-800"
                >
                  Close
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-3 space-y-2">
                {isLoadingHistory ? (
                  <div className="flex items-center justify-center py-12 text-slate-400 space-x-2 text-xs">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Loading conversations...</span>
                  </div>
                ) : conversations.length === 0 ? (
                  <div className="text-center py-12 text-slate-400 text-xs">
                    No saved conversations yet. Start chatting!
                  </div>
                ) : (
                  conversations.map((conv) => (
                    <div
                      key={conv.id}
                      role="button"
                      tabIndex={0}
                      onClick={() => handleSelectConversation(conv.id)}
                      onKeyDown={(e) => e.key === 'Enter' && handleSelectConversation(conv.id)}
                      className={`ai-bubble group flex items-center justify-between p-3 rounded-2xl border text-sm cursor-pointer focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--ai-accent)] ${
                        conv.id === conversationId
                          ? 'bg-white border-[var(--ai-accent)] text-slate-900 font-medium'
                          : 'bg-white border-slate-200 text-slate-700'
                      }`}
                    >
                      <div className="truncate flex-1 pr-2">
                        <div className="truncate">{conv.title || 'Untitled Chat'}</div>
                        <div className="text-xs text-slate-500 mt-0.5">
                          {new Date(conv.updated_at).toLocaleDateString()} &bull;{' '}
                          {formatTime(conv.updated_at)}
                        </div>
                      </div>
                      <button
                        onClick={(e) => handleDeleteConversation(e, conv.id)}
                        title="Delete conversation"
                        aria-label={`Delete conversation ${conv.title || 'Untitled Chat'}`}
                        className="opacity-0 group-hover:opacity-100 focus-visible:opacity-100 text-slate-400 hover:text-rose-600 p-2 rounded-lg transition"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))
                )}
              </div>

              <div className="p-3 border-t border-slate-200 bg-white">
                <button
                  onClick={handleNewChat}
                  className="ai-press w-full flex items-center justify-center space-x-2 py-2.5 px-3 rounded-xl bg-slate-900 text-white text-sm font-medium hover:bg-slate-800"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Start New Chat</span>
                </button>
              </div>
            </div>
          ) : (
            /* Main Chat Area */
            <div className="flex-1 flex flex-col bg-gradient-to-b from-slate-50 to-slate-100/80 overflow-hidden">
              {/* Message List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4" aria-live="polite">
                {/* Welcome Message if no messages */}
                {messages.length === 0 && (
                  <div className="text-center py-5 px-2">
                    <div className="ai-orb w-16 h-16 mx-auto flex items-center justify-center text-white mb-4" aria-hidden="true">
                      <Sparkles className="w-7 h-7 drop-shadow" />
                    </div>
                    <h4 className="font-semibold text-slate-900 text-base">
                      Hello, {user?.full_name}!
                    </h4>
                    <p className="text-sm text-slate-600 mt-1 max-w-xs mx-auto leading-relaxed">
                      {isAdmin
                        ? 'I can see every user and task. Ask me to add tasks to your panel, assign work to users, or check workloads.'
                        : 'I can see only your own tasks. Ask about statuses, priorities and deadlines, or create a new task.'}
                    </p>

                    {/* Quick Suggestion Chips */}
                    <div className="mt-5 space-y-2 text-left">
                      <div className="text-xs font-medium text-slate-500 uppercase tracking-wider text-center">
                        Try asking
                      </div>
                      <div className="flex flex-col gap-2">
                        {suggestions.map((s) => (
                          <button
                            key={s.label}
                            onClick={() => handleSuggestion(s)}
                            className="ai-press text-left text-sm bg-white text-slate-700 border border-slate-200 rounded-xl px-3.5 py-2.5 flex items-center justify-between gap-2 group focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--ai-accent)]"
                          >
                            <span>{s.label}</span>
                            <span className="text-xs text-slate-400 group-hover:text-[var(--ai-accent)] transition shrink-0">
                              {s.fill ? 'Edit' : 'Ask'} &rarr;
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Rendered Messages */}
                {messages.map((msg) => {
                  const isUser = msg.sender === 'user';
                  const tools = msg.metadata?.tools_executed as string[] | undefined;
                  const actionResult = msg.metadata?.task_action_result;
                  const isPlanMessage =
                    msg.metadata?.response_type === 'plan' ||
                    msg.content.includes('Add these steps to my to-do list') ||
                    msg.content.includes('#### Phase');

                  return (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                    >
                      <div
                        className={`ai-bubble max-w-[94%] sm:max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                          isUser
                            ? 'ai-bubble-user text-white rounded-br-md'
                            : 'bg-white border border-slate-200/80 text-slate-800 rounded-bl-md'
                        }`}
                      >
                        {isUser ? (
                          <p className="whitespace-pre-wrap">{msg.content}</p>
                        ) : (
                          renderMessageContent(msg.content)
                        )}

                        {/* Interactive Plan Action CTA */}
                        {!isUser && isAdmin && isPlanMessage && (
                          <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between">
                            <span className="text-[11px] text-slate-500 font-medium">
                              Execute Plan
                            </span>
                            <button
                              onClick={() => handleSendMessage('Add these steps to my to-do list')}
                              disabled={isLoading}
                              className="ai-press inline-flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-violet-600 hover:bg-violet-700 text-white text-xs font-semibold disabled:opacity-50"
                            >
                              <Sparkles className="w-3.5 h-3.5" />
                              <span>Add to To-Do List</span>
                            </button>
                          </div>
                        )}

                        {/* Action Outcome Badges (Notification / Plan conversion) */}
                        {!isUser && actionResult && (
                          <div className="mt-2.5 pt-2 border-t border-slate-100 space-y-1">
                            {actionResult.notification?.sent && (
                              <div className="flex items-center space-x-1.5 text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded-md">
                                <Bell className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                                <span>
                                  Notification dispatched to{' '}
                                  <strong>{actionResult.notification.recipient}</strong>
                                </span>
                              </div>
                            )}
                            {actionResult.total_created !== undefined && (
                              <div className="flex items-center space-x-1.5 text-[10px] text-purple-700 bg-purple-50 border border-purple-200 px-2 py-1 rounded-md">
                                <CheckCircle2 className="w-3 h-3 text-purple-600 flex-shrink-0" />
                                <span>
                                  <strong>{actionResult.total_created}</strong> tasks created & committed in database
                                </span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Tools Execution Indicator */}
                        {!isUser && tools && tools.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-slate-100 flex items-center space-x-1 text-[10px] text-slate-400">
                            <Database className="w-2.5 h-2.5 text-emerald-500" />
                            <span>Grounded via RAG ({tools.join(', ')})</span>
                          </div>
                        )}
                      </div>

                      {/* Timestamp */}
                      <span className="text-[10px] text-slate-400 mt-1 px-1">
                        {formatTime(msg.created_at)}
                      </span>
                    </div>
                  );
                })}

                {/* Thinking / Loading Indicator */}
                {isLoading && (
                  <div className="flex items-start space-x-2">
                    <div className="ai-bubble bg-white border border-slate-200/80 rounded-2xl rounded-bl-md px-4 py-3 flex items-center space-x-2.5 text-sm text-slate-600">
                      <span className="flex items-center space-x-1" aria-hidden="true">
                        <span className="ai-dot w-1.5 h-1.5 rounded-full bg-[var(--ai-accent)]" />
                        <span className="ai-dot w-1.5 h-1.5 rounded-full bg-[var(--ai-accent)]" />
                        <span className="ai-dot w-1.5 h-1.5 rounded-full bg-[var(--ai-accent)]" />
                      </span>
                      <span>Checking the database…</span>
                    </div>
                  </div>
                )}

                {/* Error Banner */}
                {error && (
                  <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-xl p-2.5 text-xs flex items-start space-x-2">
                    <AlertCircle className="w-4 h-4 text-rose-500 flex-shrink-0 mt-0.5" />
                    <div className="flex-1">
                      <p>{error}</p>
                      <button
                        onClick={() => setError(null)}
                        className="text-[11px] underline mt-1 font-medium hover:text-rose-800"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Input Area */}
              <div className="p-3 bg-white/90 border-t border-slate-200/80">
                <div className="relative flex items-end bg-white border border-slate-300 rounded-2xl shadow-inner focus-within:ring-2 focus-within:ring-[var(--ai-accent)] focus-within:border-transparent transition">
                  <textarea
                    ref={inputRef}
                    rows={2}
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isLoading}
                    aria-label="Message the assistant"
                    placeholder={isAdmin ? 'Add, assign or look up any task…' : 'Ask about your tasks…'}
                    className="flex-1 resize-none bg-transparent px-3.5 py-2.5 text-sm text-slate-800 placeholder-slate-400 focus:outline-none max-h-28 disabled:opacity-50"
                  />
                  <div className="p-1.5">
                    <button
                      onClick={() => handleSendMessage()}
                      disabled={isLoading || !inputMessage.trim()}
                      aria-label="Send message"
                      className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                        !inputMessage.trim() || isLoading
                          ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                          : 'ai-orb ai-press text-white'
                      }`}
                    >
                      {isLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Send className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-1.5 px-1 text-xs text-slate-500">
                  <span>Press Enter to send, Shift+Enter for new line</span>
                  {conversationId && (
                    <span className="flex items-center space-x-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                      <span>Active session</span>
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Floating 3D Orb Launcher */}
      <div className="relative flex flex-col items-center">
        <button
          onClick={() => setIsOpen(!isOpen)}
          aria-label={isOpen ? 'Close AI assistant' : 'Open AI assistant'}
          aria-expanded={isOpen}
          title={isAdmin ? 'Admin Agent' : 'My Assistant'}
          className="ai-orb ai-launcher group w-16 h-16 flex items-center justify-center text-white focus-visible:outline focus-visible:outline-4 focus-visible:outline-offset-2 focus-visible:outline-[var(--ai-accent)]"
        >
          {isOpen ? (
            <X className="w-6 h-6 drop-shadow transition-transform duration-200 group-hover:rotate-90" />
          ) : (
            <Bot className="w-7 h-7 drop-shadow" />
          )}
        </button>
        <span
          className="ai-launcher-shadow mt-1.5 w-10 h-2 rounded-full bg-slate-900/40 blur-[3px]"
          aria-hidden="true"
        />
      </div>
    </div>
  );
};
