import React, { useState, useEffect, useRef } from 'react';
import {
  chatbotService,
  ChatMessage,
  ChatConversation,
} from '../api/chatbotClient';
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
  Key,
} from 'lucide-react';

interface ChatbotWidgetProps {
  userRole?: 'admin' | 'user';
  userName?: string;
  apiKey?: string;
}

export const ChatbotWidget: React.FC<ChatbotWidgetProps> = ({
  userRole = 'user',
  userName = 'User',
}) => {
  const isAdmin = userRole === 'admin';

  // State
  const [isOpen, setIsOpen] = useState<boolean>(() => {
    return sessionStorage.getItem('chatbot_widget_open') === 'true';
  });

  const [conversationId, setConversationId] = useState<string | null>(() => {
    return sessionStorage.getItem('chatbot_conversation_id') || null;
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

  useEffect(() => {
    sessionStorage.setItem('chatbot_widget_open', isOpen ? 'true' : 'false');
  }, [isOpen]);

  useEffect(() => {
    if (conversationId) {
      sessionStorage.setItem('chatbot_conversation_id', conversationId);
    } else {
      sessionStorage.removeItem('chatbot_conversation_id');
    }
  }, [conversationId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen]);

  useEffect(() => {
    if (isOpen && !isHistoryOpen) {
      setTimeout(() => inputRef.current?.focus(), 150);
    }
  }, [isOpen, isHistoryOpen]);

  // Load conversation messages
  useEffect(() => {
    const fetchConversation = async () => {
      if (!conversationId) {
        setMessages([]);
        return;
      }
      try {
        const conv = await chatbotService.getConversation(conversationId);
        if (conv.messages) {
          setMessages(conv.messages);
        }
      } catch (err: any) {
        console.error('Failed to load conversation:', err);
        setConversationId(null);
        setMessages([]);
      }
    };

    fetchConversation();
  }, [conversationId]);

  const loadConversationsList = async () => {
    setIsLoadingHistory(true);
    try {
      const list = await chatbotService.listConversations();
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
      await chatbotService.deleteConversation(id);
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
      const response = await chatbotService.sendMessage(
        textToSend,
        conversationId || undefined
      );

      if (!conversationId && response.conversation_id) {
        setConversationId(response.conversation_id);
      }

      setMessages((prev) => {
        const withoutTemp = prev.filter((m) => m.id !== tempUserMsg.id);
        return [...withoutTemp, response.user_message, response.assistant_message];
      });
    } catch (err: any) {
      console.error('Chatbot error:', err);
      const detail =
        err.response?.data?.detail ||
        'Unable to connect to Chatbot microservice. Verify API key and network.';
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

  const suggestions = isAdmin
    ? [
        'Pending tasks per user',
        'Show all overdue tasks',
        'Show task distribution',
        'Can you create a plan for me?',
      ]
    : [
        'Show all my tasks',
        'Which tasks are still pending?',
        'High priority tasks',
        'Summarize my tasks',
      ];

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
                className="overflow-x-auto my-2.5 rounded-lg border border-slate-200 bg-white shadow-sm max-w-full"
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

          if (!trimmed) {
            return <div key={bIdx} className="h-1.5" />;
          }

          if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('• ')) {
            const bulletText = trimmed.replace(/^[-*•]\s+/, '');
            return (
              <div key={bIdx} className="flex items-start space-x-2 pl-2">
                <span className="text-slate-400 select-none">&bull;</span>
                <span dangerouslySetInnerHTML={{ __html: formatInline(bulletText) }} />
              </div>
            );
          }

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

          return (
            <p key={bIdx} dangerouslySetInnerHTML={{ __html: formatInline(trimmed) }} />
          );
        })}
      </div>
    );
  };

  const formatInline = (text: string): string => {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-slate-900">$1</strong>')
      .replace(/`(.*?)`/g, '<code class="bg-slate-100 text-slate-800 px-1 py-0.5 rounded text-[11px] font-mono">$1</code>');
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
    <div className="fixed bottom-6 right-6 z-50">
      {/* Floating Chat Panel */}
      {isOpen && (
        <div
          role="dialog"
          aria-label="Chatbot Assistant"
          className="fixed bottom-20 right-4 sm:right-6 w-[94vw] sm:w-[440px] h-[600px] max-h-[85vh] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200 transition-all"
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white px-4 py-3 flex items-center justify-between border-b border-slate-700">
            <div className="flex items-center space-x-2.5">
              <div
                className={`w-9 h-9 rounded-xl flex items-center justify-center shadow-md ${
                  isAdmin
                    ? 'bg-gradient-to-tr from-purple-600 to-indigo-500 text-white'
                    : 'bg-gradient-to-tr from-emerald-500 to-teal-400 text-white'
                }`}
              >
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center space-x-2">
                  <h3 className="font-semibold text-sm tracking-tight">AI Assistant</h3>
                  <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-amber-500/20 text-amber-200 border border-amber-400/30">
                    <Key className="w-2.5 h-2.5 text-amber-300" />
                    <span>API Key Secured</span>
                  </span>
                  {isAdmin ? (
                    <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-purple-500/20 text-purple-200 border border-purple-400/30">
                      <ShieldCheck className="w-2.5 h-2.5" />
                      <span>Admin</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/20 text-emerald-200 border border-emerald-400/30">
                      <UserIcon className="w-2.5 h-2.5" />
                      <span>User</span>
                    </span>
                  )}
                </div>
                <p className="text-[11px] text-slate-300">
                  {isAdmin ? 'Cross-user queries & planning' : 'Strict user data isolation'}
                </p>
              </div>
            </div>

            {/* Header Actions */}
            <div className="flex items-center space-x-1 text-slate-300">
              <button
                onClick={handleToggleHistory}
                title="Conversation History"
                className={`p-1.5 rounded-lg hover:text-white hover:bg-slate-800 transition ${
                  isHistoryOpen ? 'bg-slate-800 text-emerald-400' : ''
                }`}
              >
                <History className="w-4 h-4" />
              </button>
              <button
                onClick={handleNewChat}
                title="New Conversation"
                className="p-1.5 rounded-lg hover:text-white hover:bg-slate-800 transition"
              >
                <Plus className="w-4 h-4" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                title="Close Assistant"
                className="p-1.5 rounded-lg hover:text-white hover:bg-slate-800 transition"
              >
                <Minimize2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Drawer or Message List */}
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
                      onClick={() => handleSelectConversation(conv.id)}
                      className={`group flex items-center justify-between p-2.5 rounded-xl border text-xs cursor-pointer transition ${
                        conv.id === conversationId
                          ? 'bg-emerald-50 border-emerald-300 text-emerald-900 font-medium'
                          : 'bg-white border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-slate-100/60'
                      }`}
                    >
                      <div className="truncate flex-1 pr-2">
                        <div className="truncate">{conv.title || 'Untitled Chat'}</div>
                        <div className="text-[10px] text-slate-400 mt-0.5">
                          {new Date(conv.updated_at).toLocaleDateString()} &bull;{' '}
                          {formatTime(conv.updated_at)}
                        </div>
                      </div>
                      <button
                        onClick={(e) => handleDeleteConversation(e, conv.id)}
                        title="Delete conversation"
                        className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-600 p-1 rounded transition"
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
                  className="w-full flex items-center justify-center space-x-2 py-2 px-3 rounded-xl bg-slate-900 text-white text-xs font-medium hover:bg-slate-800 transition"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Start New Chat</span>
                </button>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col bg-slate-50 overflow-hidden">
              <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
                {messages.length === 0 && (
                  <div className="text-center py-6 px-4">
                    <div
                      className={`w-12 h-12 mx-auto rounded-2xl flex items-center justify-center shadow-sm mb-3 ${
                        isAdmin
                          ? 'bg-purple-100 text-purple-700'
                          : 'bg-emerald-100 text-emerald-700'
                      }`}
                    >
                      <Sparkles className="w-6 h-6" />
                    </div>
                    <h4 className="font-semibold text-slate-800 text-sm">
                      Hello, {userName}!
                    </h4>
                    <p className="text-xs text-slate-500 mt-1 max-w-xs mx-auto">
                      {isAdmin
                        ? 'I can answer questions across all users, create project plans, convert plans to tasks, or manage tasks.'
                        : 'I can help answer questions about your tasks, statuses, priorities, deadlines, or create new tasks.'}
                    </p>

                    <div className="mt-5 space-y-2 text-left">
                      <div className="text-[11px] font-medium text-slate-400 uppercase tracking-wider text-center">
                        Suggested Inquiries
                      </div>
                      <div className="flex flex-col gap-1.5">
                        {suggestions.map((prompt, idx) => (
                          <button
                            key={idx}
                            onClick={() => handleSendMessage(prompt)}
                            className="text-left text-xs bg-white hover:bg-slate-100 text-slate-700 border border-slate-200 rounded-lg px-3 py-2 transition shadow-sm flex items-center justify-between group"
                          >
                            <span>{prompt}</span>
                            <span className="text-slate-300 group-hover:text-slate-600 transition">
                              &rarr;
                            </span>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {messages.map((msg) => {
                  const isUser = msg.sender === 'user';
                  const tools = msg.metadata_?.tools_executed as string[] | undefined;
                  const actionResult = msg.metadata_?.task_action_result;
                  const isPlanMessage =
                    msg.metadata_?.response_type === 'plan' ||
                    msg.content.includes('Add these steps to my to-do list') ||
                    msg.content.includes('#### Phase');

                  return (
                    <div
                      key={msg.id}
                      className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}
                    >
                      <div
                        className={`max-w-[94%] sm:max-w-[88%] rounded-2xl px-3.5 py-2.5 text-xs shadow-sm transition ${
                          isUser
                            ? 'bg-emerald-600 text-white rounded-br-sm'
                            : 'bg-white border border-slate-200 text-slate-800 rounded-bl-sm'
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
                              onClick={() =>
                                handleSendMessage('Add these steps to my to-do list')
                              }
                              disabled={isLoading}
                              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-[11px] font-semibold shadow transition transform active:scale-95 disabled:opacity-50"
                            >
                              <Sparkles className="w-3.5 h-3.5" />
                              <span>⚡ Add to To-Do List</span>
                            </button>
                          </div>
                        )}

                        {/* Outcome Badges */}
                        {!isUser && actionResult && (
                          <div className="mt-2.5 pt-2 border-t border-slate-100 space-y-1">
                            {actionResult.notification?.sent && (
                              <div className="flex items-center space-x-1.5 text-[10px] text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded-md">
                                <Bell className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                                <span>
                                  Notification dispatched to{' '}
                                  <strong>
                                    {actionResult.notification.recipient}
                                  </strong>
                                </span>
                              </div>
                            )}
                            {actionResult.total_created !== undefined && (
                              <div className="flex items-center space-x-1.5 text-[10px] text-purple-700 bg-purple-50 border border-purple-200 px-2 py-1 rounded-md">
                                <CheckCircle2 className="w-3 h-3 text-purple-600 flex-shrink-0" />
                                <span>
                                  <strong>{actionResult.total_created}</strong> tasks
                                  created & committed in database
                                </span>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Grounding Indicator */}
                        {!isUser && tools && tools.length > 0 && (
                          <div className="mt-2 pt-2 border-t border-slate-100 flex items-center space-x-1 text-[10px] text-slate-400">
                            <Database className="w-2.5 h-2.5 text-emerald-500" />
                            <span>Grounded via RAG ({tools.join(', ')})</span>
                          </div>
                        )}
                      </div>

                      <span className="text-[10px] text-slate-400 mt-1 px-1">
                        {formatTime(msg.created_at)}
                      </span>
                    </div>
                  );
                })}

                {isLoading && (
                  <div className="flex items-start space-x-2">
                    <div className="bg-white border border-slate-200 rounded-2xl px-3.5 py-2.5 shadow-sm rounded-bl-sm flex items-center space-x-2 text-xs text-slate-500">
                      <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-600" />
                      <span>Chatbot is processing query...</span>
                    </div>
                  </div>
                )}

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
              <div className="p-3 bg-white border-t border-slate-200">
                <div className="relative flex items-end bg-slate-50 border border-slate-300 rounded-xl focus-within:ring-2 focus-within:ring-emerald-500 focus-within:border-transparent transition">
                  <textarea
                    ref={inputRef}
                    rows={1}
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isLoading}
                    placeholder="Ask about tasks, plans, or assignments..."
                    className="flex-1 resize-none bg-transparent px-3 py-2.5 text-xs text-slate-800 placeholder-slate-400 focus:outline-none max-h-24 disabled:opacity-50"
                  />
                  <div className="p-1.5">
                    <button
                      onClick={() => handleSendMessage()}
                      disabled={isLoading || !inputMessage.trim()}
                      className={`w-7 h-7 rounded-lg flex items-center justify-center transition shadow-sm ${
                        !inputMessage.trim() || isLoading
                          ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                          : isAdmin
                          ? 'bg-purple-600 hover:bg-purple-700 text-white'
                          : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                      }`}
                    >
                      {isLoading ? (
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      ) : (
                        <Send className="w-3.5 h-3.5" />
                      )}
                    </button>
                  </div>
                </div>
                <div className="flex items-center justify-between mt-1.5 px-1 text-[10px] text-slate-400">
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

      {/* Floating Action Bubble */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Toggle AI Assistant"
        className={`group flex items-center space-x-2 px-4 py-3 rounded-full shadow-lg hover:shadow-xl transition-all transform hover:-translate-y-0.5 active:translate-y-0 ${
          isOpen
            ? 'bg-slate-800 text-white ring-2 ring-slate-400/30'
            : isAdmin
            ? 'bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-700 text-white'
            : 'bg-gradient-to-r from-emerald-600 via-teal-600 to-emerald-700 text-white'
        }`}
      >
        <div className="relative">
          {isOpen ? (
            <X className="w-5 h-5 transition-transform group-hover:rotate-90 duration-200" />
          ) : (
            <>
              <Bot className="w-5 h-5" />
              <span className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-amber-400 ring-2 ring-white animate-pulse" />
            </>
          )}
        </div>
        <span className="font-semibold text-sm tracking-tight select-none">
          {isOpen ? 'Close' : 'AI Assistant'}
        </span>
      </button>
    </div>
  );
};

