'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Bot,
  Send,
  Sparkles,
  User,
  FileText,
  Clock,
  Plus,
  Trash2,
  ChevronRight,
  ExternalLink,
  ShieldCheck,
  AlertCircle,
  BookOpen,
  ShieldAlert,
  Wrench,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { AIEmployee, Conversation, Message, Citation, PendingConfirmation } from '@/types';

export default function AIEmployeeChatPage() {
  const params = useParams();
  const router = useRouter();
  const employeeId = params.id as string;

  const [employee, setEmployee] = useState<AIEmployee | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [pendingConfirmation, setPendingConfirmation] = useState<PendingConfirmation | null>(null);
  const [isConfirming, setIsConfirming] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  // Load employee and conversations on mount
  useEffect(() => {
    if (!employeeId) return;

    const loadInitialData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Fetch employee details
        const emp = await api.getAIEmployee(employeeId);
        setEmployee(emp);

        // Fetch conversations for this employee
        const convs = await api.listConversations(employeeId);
        setConversations(convs);

        if (convs.length > 0) {
          // Select the most recent conversation
          setActiveConvId(convs[0].id);
        } else {
          // Auto-create a first conversation
          const newConv = await api.createConversation(employeeId, `Chat with ${emp.name}`);
          setConversations([newConv]);
          setActiveConvId(newConv.id);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to initialize chat');
      } finally {
        setIsLoading(false);
      }
    };

    loadInitialData();
  }, [employeeId]);

  // Load messages whenever active conversation changes
  useEffect(() => {
    if (!activeConvId) return;

    const loadMessages = async () => {
      try {
        const msgs = await api.getMessages(activeConvId);
        setMessages(msgs);
      } catch (err: any) {
        setError(err.message || 'Failed to load messages');
      }
    };

    loadMessages();
  }, [activeConvId]);

  const handleNewConversation = async () => {
    if (!employee) return;
    try {
      setError(null);
      const newConv = await api.createConversation(employee.id, `New Chat (${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })})`);
      setConversations((prev) => [newConv, ...prev]);
      setActiveConvId(newConv.id);
      setMessages([]);
    } catch (err: any) {
      setError(err.message || 'Failed to create conversation');
    }
  };

  const handleDeleteConversation = async (e: React.MouseEvent, convId: string) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this conversation?')) return;

    try {
      await api.deleteConversation(convId);
      const updated = conversations.filter((c) => c.id !== convId);
      setConversations(updated);

      if (activeConvId === convId) {
        if (updated.length > 0) {
          setActiveConvId(updated[0].id);
        } else {
          setActiveConvId(null);
          setMessages([]);
        }
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete conversation');
    }
  };

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputQuery.trim() || isSending || !activeConvId) return;

    const query = inputQuery.trim();
    setInputQuery('');
    setIsSending(true);
    setError(null);

    // Optimistic user message append
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: activeConvId,
      company_id: employee?.company_id || '',
      role: 'USER',
      content: query,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await api.sendMessage(activeConvId, query);
      // Replace optimistic message with actual persisted messages
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        response.user_message,
        response.assistant_message,
      ]);

      // Check for pending tool action confirmation
      if (response.pending_confirmation) {
        setPendingConfirmation(response.pending_confirmation);
      } else {
        setPendingConfirmation(null);
      }

      // Refresh conversations list to update title
      const updatedConvs = await api.listConversations(employeeId);
      setConversations(updatedConvs);
    } catch (err: any) {
      setError(err.message || 'Failed to get response from AI Employee');
    } finally {
      setIsSending(false);
    }
  };

  const handleConfirmAction = async (confirmed: boolean) => {
    if (!pendingConfirmation || !activeConvId || isConfirming) return;
    setIsConfirming(true);
    setError(null);

    try {
      const actionId = pendingConfirmation.pending_action_id;
      const confirmText = confirmed ? 'Yes, proceed with action' : 'No, cancel action';

      // Send confirmation to conversational brain
      const response = await api.sendMessage(
        activeConvId,
        confirmText,
        actionId,
        confirmed
      );

      setMessages((prev) => [
        ...prev,
        response.user_message,
        response.assistant_message,
      ]);
      setPendingConfirmation(null);
    } catch (err: any) {
      setError(err.message || 'Failed to process confirmation');
    } finally {
      setIsConfirming(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4">
        <div className="w-10 h-10 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin" />
        <p className="text-slate-400 text-sm">Connecting to AI Employee conversational brain...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-5.5rem)] -m-6">
      {/* Top Header */}
      <header className="px-6 py-3.5 bg-slate-900/80 backdrop-blur border-b border-slate-800 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link
            href="/ai-employees"
            className="p-2 rounded-lg bg-slate-800/60 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Back to AI Employees"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>

          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-bold text-white">{employee?.name}</h1>
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                  {employee?.status}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <p className="text-xs text-slate-400">{employee?.role}</p>
                {employee?.assigned_knowledge_bases && employee.assigned_knowledge_bases.length > 0 ? (
                  <div className="hidden sm:flex items-center gap-1.5">
                    <span className="text-slate-600">•</span>
                    <span className="text-[11px] text-indigo-300 font-medium flex items-center gap-1 bg-indigo-950/50 border border-indigo-800/40 px-2 py-0.5 rounded">
                      <BookOpen className="w-3 h-3 text-indigo-400" />
                      {employee.assigned_knowledge_bases.map((k) => k.name).join(', ')}
                    </span>
                  </div>
                ) : (
                  <div className="hidden sm:flex items-center gap-1.5">
                    <span className="text-slate-600">•</span>
                    <span className="text-[11px] text-amber-400/80 italic flex items-center gap-1 bg-amber-950/30 border border-amber-900/40 px-2 py-0.5 rounded">
                      <ShieldAlert className="w-3 h-3 text-amber-400" />
                      Pure Persona Mode
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-800/60 border border-slate-700/50 text-xs text-slate-300">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Multi-Tenant Vector Isolation Active</span>
          </div>
        </div>
      </header>

      {/* Main Split Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar: Conversation Threads */}
        <aside className="w-64 lg:w-72 bg-slate-950/70 border-r border-slate-800/80 flex flex-col shrink-0">
          <div className="p-3 border-b border-slate-800/80">
            <button
              onClick={handleNewConversation}
              className="w-full py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center justify-center gap-2 shadow-sm transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>New Conversation</span>
            </button>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {conversations.length === 0 ? (
              <div className="text-center py-8 text-xs text-slate-500">
                No conversations yet.
              </div>
            ) : (
              conversations.map((c) => {
                const isActive = c.id === activeConvId;
                return (
                  <div
                    key={c.id}
                    onClick={() => setActiveConvId(c.id)}
                    className={`group flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-colors ${
                      isActive
                        ? 'bg-slate-800 text-white font-medium shadow-sm'
                        : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'
                    }`}
                  >
                    <div className="truncate flex-1 pr-2">
                      <p className="truncate">{c.title}</p>
                      <span className="text-[10px] text-slate-500">
                        {new Date(c.created_at).toLocaleDateString([], {
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                    </div>
                    <button
                      onClick={(e) => handleDeleteConversation(e, c.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-rose-400 rounded transition-opacity"
                      title="Delete thread"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* Center: Chat Window */}
        <main className="flex-1 flex flex-col bg-slate-900/40 relative">
          {error && (
            <div className="m-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Messages Feed */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full max-w-lg mx-auto text-center space-y-4">
                <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shadow-inner">
                  <Sparkles className="w-7 h-7" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    Chat with {employee?.name}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 max-w-sm">
                    {employee?.description ||
                      'Ask questions grounded in your company knowledge base documents.'}
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-2 w-full pt-2">
                  {[
                    'What is our company refund and return policy?',
                    'Summarize the key terms in our latest handbook.',
                    'How are customer warranty claims handled?',
                  ].map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => setInputQuery(prompt)}
                      className="p-3 text-left rounded-xl bg-slate-800/40 hover:bg-slate-800/80 border border-slate-700/40 text-xs text-slate-300 hover:text-white transition-colors flex items-center justify-between group"
                    >
                      <span>{prompt}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-500 group-hover:text-indigo-400 transition-colors" />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => {
                const isUser = msg.role === 'USER';
                return (
                  <div
                    key={msg.id}
                    className={`flex gap-3 max-w-3xl ${
                      isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'
                    }`}
                  >
                    <div
                      className={`w-8 h-8 rounded-lg shrink-0 flex items-center justify-center text-white ${
                        isUser
                          ? 'bg-slate-700'
                          : 'bg-gradient-to-br from-indigo-500 to-purple-600 shadow-md shadow-indigo-500/20'
                      }`}
                    >
                      {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                    </div>

                    <div className="space-y-2 max-w-[85%]">
                      <div
                        className={`p-4 rounded-2xl text-sm leading-relaxed ${
                          isUser
                            ? 'bg-indigo-600 text-white rounded-tr-none'
                            : 'bg-slate-800/90 text-slate-100 border border-slate-700/60 rounded-tl-none shadow-sm'
                        }`}
                      >
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                      </div>

                      {/* Executed Tools Badge in Assistant Message */}
                      {!isUser && msg.message_metadata?.tool_calls && Array.isArray(msg.message_metadata.tool_calls) && msg.message_metadata.tool_calls.length > 0 && (
                        <div className="pt-1">
                          <div className="flex flex-wrap gap-1.5 items-center">
                            <span className="text-[10px] text-emerald-400/80 font-mono font-medium flex items-center gap-1">
                              <Wrench className="w-3 h-3" />
                              Tools:
                            </span>
                            {msg.message_metadata.tool_calls.map((tc: any, idx: number) => (
                              <span
                                key={idx}
                                className="px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/50 text-emerald-300 text-[10px] font-mono flex items-center gap-1"
                              >
                                <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                                {tc.name || tc.tool_name || 'action'}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Grounded Sources / Citations */}
                      {!isUser && msg.citations && msg.citations.length > 0 && (
                        <div className="pt-1">
                          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 flex items-center gap-1">
                            <FileText className="w-3 h-3 text-emerald-400" />
                            Grounded Sources:
                          </p>
                          <div className="flex flex-wrap gap-2">
                            {msg.citations.map((c, i) => (
                              <button
                                key={i}
                                onClick={() => setSelectedCitation(c)}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs transition-colors"
                              >
                                <span className="font-medium text-emerald-400 truncate max-w-[160px]">
                                  {c.document_name}
                                </span>
                                {c.page_number && (
                                  <span className="text-[10px] text-slate-400">
                                    p.{c.page_number}
                                  </span>
                                )}
                                <span className="text-[10px] px-1 rounded bg-slate-900 text-slate-400 font-mono">
                                  {Math.round(c.score * 100)}%
                                </span>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      <span className="text-[10px] text-slate-500 block">
                        {new Date(msg.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                  </div>
                );
              })
            )}

            {/* Pending Tool Write Action Confirmation Card */}
            {pendingConfirmation && (
              <div className="max-w-2xl mx-auto my-4 p-5 rounded-2xl bg-amber-950/30 border-2 border-amber-500/40 shadow-xl space-y-3">
                <div className="flex items-center gap-2.5 text-amber-400 font-semibold text-sm">
                  <AlertTriangle className="w-5 h-5 text-amber-400 animate-bounce" />
                  <span>Action Requires Your Confirmation</span>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed">
                  {pendingConfirmation.message ||
                    `The AI Employee is requesting permission to execute write operation "${pendingConfirmation.tool_name}".`}
                </p>

                <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 font-mono text-[11px] text-slate-300 space-y-1">
                  <div className="text-amber-400 font-bold">Tool: {pendingConfirmation.tool_name}</div>
                  <pre className="text-slate-400 overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(pendingConfirmation.arguments, null, 2)}
                  </pre>
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => handleConfirmAction(false)}
                    disabled={isConfirming}
                    className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                  >
                    <XCircle className="w-4 h-4 text-rose-400" />
                    <span>Cancel Action</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => handleConfirmAction(true)}
                    disabled={isConfirming}
                    className="px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold flex items-center gap-1.5 shadow-md shadow-amber-500/20 transition-all disabled:opacity-50"
                  >
                    <CheckCircle2 className="w-4 h-4 text-slate-950" />
                    <span>{isConfirming ? 'Executing...' : 'Confirm & Execute'}</span>
                  </button>
                </div>
              </div>
            )}

            {/* Typing Indicator */}
            {isSending && (
              <div className="flex gap-3 max-w-3xl mr-auto">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="p-4 rounded-2xl bg-slate-800/90 border border-slate-700/60 rounded-tl-none flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
                  <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse [animation-delay:0.2s]" />
                  <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse [animation-delay:0.4s]" />
                  <span className="text-xs text-slate-400 ml-1">
                    Retrieving knowledge &amp; thinking...
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Bottom Chat Input Bar */}
          <div className="p-4 bg-slate-950/80 backdrop-blur border-t border-slate-800">
            <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto relative flex items-center">
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder={`Ask ${employee?.name || 'AI Employee'} anything about company knowledge...`}
                disabled={isSending || !activeConvId}
                className="w-full pl-4 pr-12 py-3.5 rounded-xl bg-slate-900 border border-slate-700/80 text-white placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={!inputQuery.trim() || isSending || !activeConvId}
                className="absolute right-2 p-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white disabled:text-slate-600 transition-colors"
                title="Send Message"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
            <p className="text-center text-[11px] text-slate-500 mt-2">
              All responses are grounded strictly in your company documents. No cross-tenant data leakage.
            </p>
          </div>
        </main>
      </div>

      {/* Citation Details Drawer Modal */}
      {selectedCitation && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-xl p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2 text-emerald-400">
                <FileText className="w-5 h-5" />
                <h3 className="font-semibold text-white text-sm">Citation Source Details</h3>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-slate-400 hover:text-white text-xs"
              >
                ✕ Close
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between text-slate-400">
                <span>Document:</span>
                <span className="font-mono text-slate-200">{selectedCitation.document_name}</span>
              </div>
              {selectedCitation.page_number && (
                <div className="flex items-center justify-between text-slate-400">
                  <span>Page:</span>
                  <span className="text-slate-200">{selectedCitation.page_number}</span>
                </div>
              )}
              {selectedCitation.header_path && (
                <div className="flex items-center justify-between text-slate-400">
                  <span>Section:</span>
                  <span className="text-slate-200">{selectedCitation.header_path}</span>
                </div>
              )}
              <div className="flex items-center justify-between text-slate-400">
                <span>Similarity Score:</span>
                <span className="font-mono text-emerald-400">{selectedCitation.score}</span>
              </div>
            </div>

            <div className="pt-2">
              <span className="text-xs font-semibold text-slate-400 block mb-1.5">
                Retrieved Context Excerpt:
              </span>
              <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto font-mono">
                {selectedCitation.preview || 'No preview available.'}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
