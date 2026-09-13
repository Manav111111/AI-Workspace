'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  MessageSquare,
  Bot,
  Mic,
  Video,
  Sparkles,
  ArrowRight,
  Clock,
  Trash2,
  AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';
import { AIEmployee, Conversation } from '@/types';

export default function ConversationsPage() {
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [emps, convs] = await Promise.all([
        api.getAIEmployees(),
        api.listConversations(),
      ]);
      setEmployees(emps);
      setConversations(convs);
    } catch (err: any) {
      setError(err.message || 'Failed to load conversations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleDelete = async (convId: string) => {
    if (!confirm('Are you sure you want to delete this conversation?')) return;
    try {
      await api.deleteConversation(convId);
      setConversations((prev) => prev.filter((c) => c.id !== convId));
    } catch (err: any) {
      setError(err.message || 'Failed to delete conversation');
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-8">
      {/* Header */}
      <div>
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono mb-2">
          <span>Phase 2 Grounded Conversational Brain • LIVE</span>
        </div>
        <h1 className="text-2xl font-bold text-slate-100">Conversations &amp; Testing Console</h1>
        <p className="text-sm text-slate-400 mt-1">
          Interact with your AI Employees grounded in company documents with full source citations.
        </p>
      </div>

      {error && (
        <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Select an AI Employee to Chat With */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Start a Chat with an AI Employee
        </h2>

        {loading ? (
          <div className="h-24 flex items-center justify-center text-slate-500 text-xs">
            Loading AI Employees...
          </div>
        ) : employees.length === 0 ? (
          <div className="p-6 rounded-xl bg-slate-900/60 border border-slate-800 text-center space-y-2">
            <Bot className="w-8 h-8 text-slate-500 mx-auto" />
            <p className="text-sm text-slate-300">No AI Employees created yet.</p>
            <Link
              href="/ai-employees"
              className="inline-flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-medium"
            >
              <span>Create an AI Employee</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {employees.map((emp) => (
              <div
                key={emp.id}
                className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
                      <Bot className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white text-sm">{emp.name}</h3>
                      <p className="text-xs text-slate-400">{emp.role}</p>
                    </div>
                  </div>
                  {emp.description && (
                    <p className="text-xs text-slate-400 line-clamp-2 mb-4">
                      {emp.description}
                    </p>
                  )}
                </div>

                <Link
                  href={`/ai-employees/${emp.id}/chat`}
                  className="w-full py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold flex items-center justify-center gap-2 transition-colors mt-2"
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Open Chat Console</span>
                </Link>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Recent Conversation History */}
      <section className="space-y-4">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Recent Conversations
        </h2>

        {loading ? (
          <div className="h-20 flex items-center justify-center text-slate-500 text-xs">
            Loading conversations...
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-6 rounded-xl bg-slate-900/40 border border-slate-800/80 text-center text-xs text-slate-500">
            No past conversations recorded. Start a chat above!
          </div>
        ) : (
          <div className="divide-y divide-slate-800/60 rounded-xl bg-slate-900/40 border border-slate-800/80 overflow-hidden">
            {conversations.map((c) => {
              const emp = employees.find((e) => e.id === c.ai_employee_id);
              return (
                <div
                  key={c.id}
                  className="p-4 hover:bg-slate-800/40 transition-colors flex items-center justify-between gap-4"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center text-indigo-400 shrink-0">
                      <MessageSquare className="w-4 h-4" />
                    </div>
                    <div>
                      <h4 className="text-sm font-medium text-slate-200">{c.title}</h4>
                      <div className="flex items-center gap-2 text-xs text-slate-500 mt-0.5">
                        <span>With {emp ? emp.name : 'AI Employee'}</span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {new Date(c.created_at).toLocaleString([], {
                            month: 'short',
                            day: 'numeric',
                            hour: '2-digit',
                            minute: '2-digit',
                          })}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Link
                      href={`/ai-employees/${c.ai_employee_id}/chat`}
                      className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
                    >
                      Resume
                    </Link>
                    <button
                      onClick={() => handleDelete(c.id)}
                      className="p-1.5 text-slate-500 hover:text-rose-400 rounded transition-colors"
                      title="Delete conversation"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Multimodal Roadmap Cards */}
      <section className="pt-4 border-t border-slate-800/80">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-4">
          Decoupled Multi-Channel Architecture
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-emerald-500/5 border border-emerald-500/20">
            <div className="flex items-center gap-2 text-emerald-400 mb-2">
              <MessageSquare className="w-4 h-4" />
              <span className="text-xs font-bold uppercase tracking-wider">Phase 2 • LIVE</span>
            </div>
            <h3 className="font-semibold text-white text-sm">Grounded Chat Engine</h3>
            <p className="mt-1 text-xs text-slate-400">
              Qdrant vector retrieval, citations, bounded context, and LLM reasoning.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="flex items-center gap-2 text-indigo-400 mb-2">
              <Mic className="w-4 h-4" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Upcoming</span>
            </div>
            <h3 className="font-semibold text-white text-sm">Real-Time Voice Streaming</h3>
            <p className="mt-1 text-xs text-slate-400">
              Low-latency STT and TTS re-using this same conversational brain.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="flex items-center gap-2 text-pink-400 mb-2">
              <Video className="w-4 h-4" />
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500">Upcoming</span>
            </div>
            <h3 className="font-semibold text-white text-sm">3D Avatar Presentation</h3>
            <p className="mt-1 text-xs text-slate-400">
              Decoupled presentation layer with facial blendshapes and gestures.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
