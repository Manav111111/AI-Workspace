'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  MessageSquare,
  Bot,
  ArrowRight,
  Clock,
  Trash2,
  AlertCircle,
  Plus,
} from 'lucide-react';
import { api } from '@/lib/api';
import { AIEmployee, Conversation } from '@/types';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Card, CardContent } from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';

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
    <div className="max-w-7xl mx-auto space-y-6">
      <PageHeader
        title="Conversations & Testing"
        description="Review past sessions and interact with your AI Employees grounded in company knowledge base documents."
        badge={<Badge variant="orange">Multi-Turn History</Badge>}
      />

      {error && (
        <div className="p-3.5 rounded-lg bg-rose-950/40 border border-rose-900/60 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}

      {/* Select an AI Employee to Chat With */}
      <section className="space-y-3">
        <h2 className="text-[11px] font-mono uppercase tracking-wider text-[#737373]">
          Start a Session with an AI Employee
        </h2>

        {loading ? (
          <div className="h-24 flex items-center justify-center text-[#737373] text-xs font-mono">
            Loading AI Employees...
          </div>
        ) : employees.length === 0 ? (
          <EmptyState
            icon={Bot}
            title="No AI Employees created"
            description="Create an AI employee to begin interactive conversations."
            actionText="Create AI Employee"
            actionIcon={Plus}
            onAction={() => (window.location.href = '/ai-employees')}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {employees.map((emp) => (
              <Link
                key={emp.id}
                href={`/ai-employees/${emp.id}/chat`}
                className="group"
              >
                <div className="p-4 rounded-lg bg-[#101010] border border-[#262626] group-hover:border-[#FF9D00]/50 transition-all flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] group-hover:bg-[#FF9D00]/10 transition-colors shrink-0">
                      <Bot className="w-4 h-4" />
                    </div>
                    <div>
                      <h3 className="text-xs font-semibold text-[#F5F5F5] group-hover:text-[#FF9D00] transition-colors">
                        {emp.name}
                      </h3>
                      <p className="text-[11px] text-[#A1A1AA] font-mono mt-0.5">{emp.role}</p>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-[#737373] group-hover:text-[#FF9D00] group-hover:translate-x-0.5 transition-all" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* Recent Conversation History List */}
      <section className="space-y-3">
        <h2 className="text-[11px] font-mono uppercase tracking-wider text-[#737373]">
          Recent Conversation Sessions ({conversations.length})
        </h2>

        {loading ? (
          <div className="h-24 flex items-center justify-center text-[#737373] text-xs font-mono">
            Loading conversation threads...
          </div>
        ) : conversations.length === 0 ? (
          <div className="p-8 text-center border border-dashed border-[#262626] rounded-lg bg-[#101010] text-xs text-[#737373]">
            No active conversation sessions found. Click on an AI Employee above to start chatting!
          </div>
        ) : (
          <Card>
            <div className="divide-y divide-[#262626]">
              {conversations.map((c) => {
                const emp = employees.find((e) => e.id === c.ai_employee_id);
                return (
                  <div
                    key={c.id}
                    className="p-4 flex items-center justify-between hover:bg-[#151515]/60 transition-colors"
                  >
                    <div className="flex items-center gap-3.5 truncate pr-4">
                      <div className="w-8 h-8 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#737373] shrink-0">
                        <MessageSquare className="w-4 h-4 text-[#FF9D00]" />
                      </div>
                      <div className="truncate">
                        <Link
                          href={`/ai-employees/${c.ai_employee_id}/chat`}
                          className="text-xs font-medium text-[#F5F5F5] hover:text-[#FF9D00] transition-colors block truncate"
                        >
                          {c.title}
                        </Link>
                        <div className="flex items-center gap-2 text-[11px] text-[#737373] mt-0.5">
                          <span className="text-[#FF9D00] font-mono font-medium">
                            {emp?.name || 'AI Employee'}
                          </span>
                          <span>&bull;</span>
                          <span className="flex items-center gap-1 font-mono">
                            <Clock className="w-3 h-3" />
                            {new Date(c.created_at).toLocaleDateString([], {
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <Link
                        href={`/ai-employees/${c.ai_employee_id}/chat`}
                        className="px-3 py-1.5 rounded-lg bg-[#151515] hover:bg-[#1E1E1E] border border-[#262626] text-xs text-[#F5F5F5] font-medium flex items-center gap-1.5 transition-colors"
                      >
                        <span>Resume</span>
                        <ArrowRight className="w-3.5 h-3.5 text-[#FF9D00]" />
                      </Link>
                      <button
                        onClick={() => handleDelete(c.id)}
                        className="p-1.5 text-[#737373] hover:text-rose-400 hover:bg-[#1A1A1A] rounded transition-colors"
                        title="Delete session"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}
      </section>
    </div>
  );
}
