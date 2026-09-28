'use client';

import React, { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Bot,
  Send,
  User,
  FileText,
  Clock,
  Plus,
  Trash2,
  ChevronRight,
  ShieldCheck,
  AlertCircle,
  BookOpen,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  X,
} from 'lucide-react';
import { api } from '@/lib/api';
import { AIEmployee, Conversation, Message, Citation, PendingConfirmation } from '@/types';
import Badge from '@/components/ui/Badge';
import Button from '@/components/ui/Button';

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

        const emp = await api.getAIEmployee(employeeId);
        setEmployee(emp);

        const convs = await api.listConversations(employeeId);
        setConversations(convs);

        if (convs.length > 0) {
          setActiveConvId(convs[0].id);
        } else {
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
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== tempUserMsg.id),
        response.user_message,
        response.assistant_message,
      ]);

      if (response.pending_confirmation) {
        setPendingConfirmation(response.pending_confirmation);
      } else {
        setPendingConfirmation(null);
      }

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
      <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-4 font-sans">
        <div className="w-10 h-10 border-2 border-[#FF9D00]/20 border-t-[#FF9D00] rounded-full animate-spin" />
        <p className="text-[#737373] text-xs font-mono">Connecting to AI Employee conversational brain...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[calc(100vh-5.5rem)] -m-6 font-sans">
      {/* Top Header */}
      <header className="px-6 py-3.5 bg-[#080808]/90 backdrop-blur border-b border-[#262626] flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link
            href="/ai-employees"
            className="p-2 rounded-lg bg-[#151515] hover:bg-[#1A1A1A] text-[#737373] hover:text-[#F5F5F5] border border-[#262626] transition-editorial"
            title="Back to AI Employees"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>

          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] shadow-card shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-display font-bold text-[#F5F5F5] tracking-tight">{employee?.name}</h1>
                <Badge variant={employee?.status === 'ACTIVE' ? 'forest' : 'neutral'} dot>
                  {employee?.status}
                </Badge>
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <p className="text-xs text-[#FF9D00] font-mono">{employee?.role}</p>
                {employee?.assigned_knowledge_bases && employee.assigned_knowledge_bases.length > 0 ? (
                  <div className="hidden sm:flex items-center gap-1.5">
                    <span className="text-[#262626]">•</span>
                    <span className="text-[11px] text-[#F5F5F5] font-medium flex items-center gap-1 bg-[#151515] border border-[#262626] px-2 py-0.5 rounded">
                      <BookOpen className="w-3 h-3 text-[#FF9D00]" />
                      {employee.assigned_knowledge_bases.map((k) => k.name).join(', ')}
                    </span>
                  </div>
                ) : (
                  <div className="hidden sm:flex items-center gap-1.5">
                    <span className="text-[#262626]">•</span>
                    <span className="text-[11px] text-[#FFC247] italic flex items-center gap-1 bg-orange-950/30 border border-orange-900/40 px-2 py-0.5 rounded">
                      <ShieldAlert className="w-3 h-3 text-[#FF9D00]" />
                      Pure Persona Mode
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 rounded-md bg-[#101010] border border-[#262626] text-xs text-[#A1A1AA]">
            <ShieldCheck className="w-3.5 h-3.5 text-[#FF9D00]" />
            <span className="font-mono text-[11px]">Tenant Boundary Enforced</span>
          </div>
        </div>
      </header>

      {/* Main Split Layout */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar: Conversation Threads */}
        <aside className="w-64 lg:w-72 bg-[#080808] border-r border-[#262626] flex flex-col shrink-0">
          <div className="p-3 border-b border-[#262626]">
            <Button
              variant="primary"
              size="sm"
              onClick={handleNewConversation}
              icon={Plus}
              className="w-full"
            >
              New Conversation
            </Button>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {conversations.length === 0 ? (
              <div className="text-center py-8 text-xs text-[#737373] font-mono">
                No conversations yet.
              </div>
            ) : (
              conversations.map((c) => {
                const isActive = c.id === activeConvId;
                return (
                  <div
                    key={c.id}
                    onClick={() => setActiveConvId(c.id)}
                    className={`group flex items-center justify-between p-2.5 rounded-lg text-xs cursor-pointer transition-editorial ${
                      isActive
                        ? 'bg-[#151515] text-[#F5F5F5] font-semibold border border-[#262626] shadow-card'
                        : 'text-[#737373] hover:bg-[#101010] hover:text-[#F5F5F5]'
                    }`}
                  >
                    <div className="truncate flex-1 pr-2">
                      <p className="truncate">{c.title}</p>
                      <span className="text-[10px] text-[#737373] font-mono">
                        {new Date(c.created_at).toLocaleDateString([], {
                          month: 'short',
                          day: 'numeric',
                        })}
                      </span>
                    </div>
                    <button
                      onClick={(e) => handleDeleteConversation(e, c.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-[#737373] hover:text-rose-400 rounded transition-editorial"
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
        <main className="flex-1 flex flex-col bg-[#050505] relative">
          {error && (
            <div className="m-4 p-3 rounded-xl bg-rose-950/60 border border-rose-800/50 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Messages Feed */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full max-w-lg mx-auto text-center space-y-4">
                <div className="w-12 h-12 rounded-xl bg-[#101010] border border-[#262626] flex items-center justify-center text-[#FF9D00] shadow-card">
                  <Bot className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-display font-bold text-[#F5F5F5] tracking-tight">
                    Chat with {employee?.name}
                  </h3>
                  <p className="text-xs text-[#737373] mt-1 max-w-sm leading-relaxed font-sans">
                    {employee?.description ||
                      'Ask questions grounded in your company knowledge base documents.'}
                  </p>
                </div>

                <div className="grid grid-cols-1 gap-2 w-full pt-2">
                  {[
                    'What is our company refund and return policy?',
                    'Summarize key terms from our uploaded documentation.',
                    'How are warranty or support inquiries handled?',
                  ].map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => setInputQuery(prompt)}
                      className="p-3 text-left rounded-xl bg-[#101010] hover:bg-[#151515] border border-[#262626] text-xs text-[#A1A1AA] hover:text-[#F5F5F5] transition-editorial flex items-center justify-between group shadow-card"
                    >
                      <span>{prompt}</span>
                      <ChevronRight className="w-3.5 h-3.5 text-[#737373] group-hover:text-[#FF9D00] transition-editorial" />
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
                          ? 'bg-[#151515] border border-[#262626]'
                          : 'bg-[#151515] border border-[#262626] text-[#FF9D00]'
                      }`}
                    >
                      {isUser ? <User className="w-4 h-4 text-[#A1A1AA]" /> : <Bot className="w-4 h-4 text-[#FF9D00]" />}
                    </div>

                    <div className="space-y-2 flex-1">
                      <div
                        className={`p-4 rounded-xl text-xs sm:text-sm leading-relaxed ${
                          isUser
                            ? 'bg-[#1A1A1A] border border-[#262626] text-[#F5F5F5] rounded-tr-none'
                            : 'bg-[#101010] border border-[#262626] text-[#F5F5F5] rounded-tl-none shadow-card'
                        }`}
                      >
                        <div className="whitespace-pre-wrap">{msg.content}</div>

                        {/* RAG Citations Section */}
                        {msg.citations && msg.citations.length > 0 && (
                          <div className="mt-3.5 pt-3 border-t border-[#262626]">
                            <div className="flex items-center gap-1.5 text-[11px] font-semibold text-[#737373] mb-2 font-mono">
                              <BookOpen className="w-3.5 h-3.5 text-[#FF9D00]" />
                              <span>Ground Truth Citations ({msg.citations.length}):</span>
                            </div>
                            <div className="flex flex-wrap gap-2">
                              {msg.citations.map((c, idx) => (
                                <button
                                  key={idx}
                                  onClick={() => setSelectedCitation(c)}
                                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#151515] hover:bg-[#1A1A1A] border border-[#262626] hover:border-[#383838] text-[11px] text-[#A1A1AA] hover:text-[#F5F5F5] transition-editorial group"
                                >
                                  <FileText className="w-3 h-3 text-[#FF9D00]" />
                                  <span className="font-medium truncate max-w-[150px]">
                                    {c.document_name || (c as any).document_title || `Doc #${c.document_id?.slice(0, 6)}`}
                                  </span>
                                  <span className="text-[10px] text-[#737373] font-mono">
                                    p.{c.page_number || 1}
                                  </span>
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>

                      <div className="flex items-center gap-2 px-1 text-[10px] text-[#737373] font-mono">
                        <Clock className="w-3 h-3" />
                        <span>
                          {new Date(msg.created_at).toLocaleTimeString([], {
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                    </div>
                  </div>
                );
              })
            )}

            {isSending && (
              <div className="flex gap-3 max-w-3xl mr-auto">
                <div className="w-8 h-8 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
                <div className="p-4 rounded-xl bg-[#101010] border border-[#262626] text-xs text-[#737373] rounded-tl-none flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#FF9D00] animate-bounce" />
                  <div className="w-2 h-2 rounded-full bg-[#FF9D00] animate-bounce delay-100" />
                  <div className="w-2 h-2 rounded-full bg-[#FF9D00] animate-bounce delay-200" />
                  <span className="ml-1 text-[11px]">Consulting knowledge base &amp; reasoning...</span>
                </div>
              </div>
            )}

            {/* Pending Tool Action Confirmation Card */}
            {pendingConfirmation && (
              <div className="max-w-xl mx-auto p-4 rounded-xl bg-[#101010] border border-orange-800/60 shadow-card space-y-3 animate-in fade-in slide-in-from-bottom-2">
                <div className="flex items-center gap-2 text-[#FFC247] font-semibold text-xs">
                  <AlertTriangle className="w-4 h-4 text-[#FF9D00] shrink-0" />
                  <span>Human Confirmation Required for Agent Tool Action</span>
                </div>
                <div className="text-xs text-[#A1A1AA] space-y-1">
                  <p>
                    Tool: <strong className="text-[#FFC247] font-mono">{pendingConfirmation.tool_name}</strong>
                  </p>
                  <pre className="p-2.5 rounded-lg bg-[#050505] border border-[#262626] text-[11px] font-mono text-[#FFC247] overflow-x-auto">
                    {JSON.stringify(pendingConfirmation.arguments || (pendingConfirmation as any).parameters || {}, null, 2)}
                  </pre>
                </div>
                <div className="flex items-center justify-end gap-2 pt-1">
                  <Button
                    variant="danger"
                    size="sm"
                    disabled={isConfirming}
                    onClick={() => handleConfirmAction(false)}
                    icon={XCircle}
                  >
                    Reject Action
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    disabled={isConfirming}
                    onClick={() => handleConfirmAction(true)}
                    icon={CheckCircle2}
                  >
                    Authorize Action
                  </Button>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div className="p-4 bg-[#080808] border-t border-[#262626]">
            <form onSubmit={handleSendMessage} className="flex items-center gap-2">
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder={`Ask ${employee?.name || 'AI Employee'} a question...`}
                disabled={isSending || !activeConvId}
                className="flex-1 px-4 py-2.5 bg-[#101010] border border-[#262626] rounded-xl text-xs sm:text-sm text-[#F5F5F5] placeholder-[#737373] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40 focus:border-[#FF9D00] transition-editorial"
              />
              <Button
                type="submit"
                variant="primary"
                size="md"
                disabled={!inputQuery.trim() || isSending || !activeConvId}
                icon={Send}
              >
                Send
              </Button>
            </form>
          </div>
        </main>
      </div>

      {/* Citation Detail Modal */}
      {selectedCitation && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-lg p-6 shadow-card max-h-[80vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262626]">
              <div className="flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-[#FF9D00]" />
                <h3 className="text-sm font-display font-bold text-[#F5F5F5]">Citation Details</h3>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-[#737373] hover:text-[#F5F5F5] p-1 rounded hover:bg-[#151515]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-2 text-xs text-[#A1A1AA]">
              <p>
                <strong className="text-[#737373]">Document: </strong>
                <span className="text-[#F5F5F5] font-medium">{selectedCitation.document_name || (selectedCitation as any).document_title || 'Document'}</span>
              </p>
              <p>
                <strong className="text-[#737373]">Page: </strong>
                <span className="font-mono text-[#FFC247]">{selectedCitation.page_number || 1}</span>
              </p>
              <div className="mt-3">
                <strong className="text-[#737373] block mb-1">Snippet Extract:</strong>
                <div className="p-3 rounded-lg bg-[#151515] border border-[#262626] text-[#F5F5F5] leading-relaxed font-mono text-[11px]">
                  {selectedCitation.preview || (selectedCitation as any).snippet}
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setSelectedCitation(null)}
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

