'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import { AuditEvent } from '@/types';
import {
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  Copy,
  Download,
  Filter,
  KeyRound,
  Layers,
  Lock,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  Terminal,
  UserCheck,
  Wrench,
  X,
  Zap,
} from 'lucide-react';

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Filters
  const [selectedEventType, setSelectedEventType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Event & Drawer
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [copiedId, setCopiedId] = useState(false);
  const [copiedPayload, setCopiedPayload] = useState(false);

  useEffect(() => {
    loadAuditLogs();
  }, []);

  async function loadAuditLogs() {
    setLoading(true);
    try {
      const data = await api.listAuditLogs({ limit: 50 });
      setEvents(data);
    } catch (err) {
      console.error('Failed to load audit logs:', err);
    } finally {
      setLoading(false);
    }
  }

  async function refreshData() {
    setRefreshing(true);
    try {
      const data = await api.listAuditLogs({
        event_type: selectedEventType !== 'ALL' ? selectedEventType : undefined,
        limit: 50,
      });
      setEvents(data);
    } catch (err) {
      console.error('Failed to refresh audit logs:', err);
    } finally {
      setRefreshing(false);
    }
  }

  const copyToClipboard = (text: string, isId: boolean = true) => {
    navigator.clipboard.writeText(text);
    if (isId) {
      setCopiedId(true);
      setTimeout(() => setCopiedId(false), 2000);
    } else {
      setCopiedPayload(true);
      setTimeout(() => setCopiedPayload(false), 2000);
    }
  };

  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      if (selectedEventType !== 'ALL' && e.event_type !== selectedEventType) {
        return false;
      }
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesEvent = e.event_type.toLowerCase().includes(query);
        const matchesResource = e.resource_type.toLowerCase().includes(query);
        const matchesResourceId = e.resource_id?.toLowerCase().includes(query);
        const matchesTrace = e.trace_id?.toLowerCase().includes(query);
        if (!matchesEvent && !matchesResource && !matchesResourceId && !matchesTrace) {
          return false;
        }
      }
      return true;
    });
  }, [events, selectedEventType, searchQuery]);

  // Color generator for event type badges
  const getEventBadgeStyle = (eventType: string) => {
    const t = eventType.toUpperCase();
    if (t.includes('EXCEEDED') || t.includes('FAIL') || t.includes('DENIED')) {
      return {
        bg: 'bg-rose-500/10',
        text: 'text-rose-400',
        border: 'border-rose-500/30',
        icon: AlertTriangle,
      };
    }
    if (t.includes('TOOL') || t.includes('ACTION')) {
      return {
        bg: 'bg-emerald-500/10',
        text: 'text-emerald-400',
        border: 'border-emerald-500/30',
        icon: Wrench,
      };
    }
    if (t.includes('BUDGET') || t.includes('OVERRIDE')) {
      return {
        bg: 'bg-amber-500/10',
        text: 'text-amber-400',
        border: 'border-amber-500/30',
        icon: AlertOctagon,
      };
    }
    if (t.includes('AUTH') || t.includes('LOGIN')) {
      return {
        bg: 'bg-cyan-500/10',
        text: 'text-cyan-400',
        border: 'border-cyan-500/30',
        icon: KeyRound,
      };
    }
    return {
      bg: 'bg-indigo-500/10',
      text: 'text-indigo-400',
      border: 'border-indigo-500/30',
      icon: Shield,
    };
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Lock className="w-6 h-6 text-indigo-400" />
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Enterprise Audit Trail
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
              Append-Only Immutable
            </span>
          </div>
          <p className="text-sm text-slate-400">
            Tamper-evident operational audit events, policy changes, tool invocations, and tenant security logs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={refreshData}
            disabled={refreshing}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-700/80 hover:bg-slate-800 text-slate-200 text-sm font-medium transition shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-indigo-400' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Compliance Guarantee Banner */}
      <div className="p-4 rounded-xl bg-slate-900/40 border border-slate-800 backdrop-blur-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="font-semibold text-slate-200">
              Automated Redaction & Isolation Guarantees
            </div>
            <div className="text-slate-400">
              All payload metadata is stripped of API keys, bearer tokens, passwords, and PII prior to persistence.
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 font-mono text-[11px] text-slate-400">
          <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800">
            Retention: 365 Days
          </span>
          <span className="px-2 py-0.5 rounded bg-slate-950 border border-slate-800">
            Tenant Isolated
          </span>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-xl border border-slate-800">
        <div className="flex flex-wrap items-center gap-3">
          {/* Event Type Filter */}
          <div className="relative">
            <select
              value={selectedEventType}
              onChange={(e) => {
                setSelectedEventType(e.target.value);
              }}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-2 pr-8 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Event Types</option>
              <option value="AUTH_LOGIN">AUTH_LOGIN</option>
              <option value="AGENT_ACTION">AGENT_ACTION</option>
              <option value="TOOL_INVOCATION">TOOL_INVOCATION</option>
              <option value="BUDGET_OVERRIDE">BUDGET_OVERRIDE</option>
              <option value="BUDGET_EXCEEDED">BUDGET_EXCEEDED</option>
              <option value="PROMPT_MODIFIED">PROMPT_MODIFIED</option>
              <option value="PLAYGROUND_SESSION_CREATED">PLAYGROUND_SESSION_CREATED</option>
            </select>
          </div>
        </div>

        {/* Search input */}
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search resource, event, or trace ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-indigo-500 placeholder-slate-500"
          />
        </div>
      </div>

      {/* Main Content Area: Audit Trail Table */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="px-5 py-4 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-semibold text-white">Immutable Event Log</h2>
            <span className="text-xs text-slate-500">({filteredEvents.length} recorded)</span>
          </div>
          <span className="text-xs text-slate-400">Strict Append-Only Storage</span>
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
            <RefreshCw className="w-6 h-6 animate-spin text-indigo-400" />
            <p className="text-sm">Loading audit events...</p>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="py-16 text-center text-slate-400">
            <Lock className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-300">No audit events found</p>
            <p className="text-xs text-slate-500 mt-1">
              Audit events are recorded automatically during auth, budget checks, tool executions, and config changes.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/50 text-slate-400 font-medium">
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Event Type</th>
                  <th className="py-3 px-4">Resource Target</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4">Trace Correlation</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {filteredEvents.map((ev) => {
                  const badge = getEventBadgeStyle(ev.event_type);
                  const Icon = badge.icon;

                  return (
                    <tr
                      key={ev.id}
                      onClick={() => setSelectedEvent(ev)}
                      className="hover:bg-slate-800/40 cursor-pointer transition"
                    >
                      <td className="py-3 px-4 text-slate-400 font-mono">
                        {new Date(ev.created_at).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold font-mono border ${badge.bg} ${badge.text} ${badge.border}`}
                        >
                          <Icon className="w-3 h-3" />
                          {ev.event_type}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-semibold text-slate-300">
                          {ev.resource_type}
                        </span>
                        {ev.resource_id && (
                          <span className="font-mono text-slate-500 text-[11px] block truncate max-w-[200px]">
                            id: {ev.resource_id}
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-300 font-mono text-[11px]">
                        {ev.actor_id ? (
                          <span className="truncate block max-w-[140px]">
                            user_{ev.actor_id.slice(0, 8)}
                          </span>
                        ) : (
                          <span className="text-slate-500">SYSTEM</span>
                        )}
                      </td>
                      <td className="py-3 px-4 font-mono text-indigo-400 text-[11px]">
                        {ev.trace_id ? (
                          <span className="truncate block max-w-[180px]">
                            {ev.trace_id.slice(0, 16)}...
                          </span>
                        ) : (
                          <span className="text-slate-600">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedEvent(ev);
                          }}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-400 hover:text-indigo-300 transition text-[11px] font-medium"
                        >
                          Inspect Event
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Event Inspector Modal / Drawer */}
      {selectedEvent && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-xl bg-slate-950 border-l border-slate-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-5 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Shield className="w-5 h-5 text-indigo-400" />
                  <span className="text-sm font-semibold text-white">Audit Event Details</span>
                </div>
                <div className="text-xs font-mono text-slate-400">
                  id: {selectedEvent.id}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() =>
                    copyToClipboard(JSON.stringify(selectedEvent, null, 2), false)
                  }
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs transition"
                >
                  {copiedPayload ? (
                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                  ) : (
                    <Download className="w-3.5 h-3.5" />
                  )}
                  Export JSON
                </button>
                <button
                  onClick={() => setSelectedEvent(null)}
                  className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Event Summary Grid */}
            <div className="p-5 space-y-4 flex-1 overflow-y-auto text-xs">
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Event Type</span>
                  <span className="font-mono font-semibold text-indigo-400">
                    {selectedEvent.event_type}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Resource Target</span>
                  <span className="font-medium text-white">
                    {selectedEvent.resource_type}{' '}
                    {selectedEvent.resource_id && `(${selectedEvent.resource_id})`}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Actor Identity</span>
                  <span className="font-mono text-slate-200">
                    {selectedEvent.actor_id || 'SYSTEM_INTERNAL'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-400">Timestamp</span>
                  <span className="font-mono text-slate-300">
                    {new Date(selectedEvent.created_at).toISOString()}
                  </span>
                </div>
                {selectedEvent.trace_id && (
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Trace Correlation</span>
                    <span className="font-mono text-indigo-400">
                      {selectedEvent.trace_id}
                    </span>
                  </div>
                )}
              </div>

              {/* Safe Metadata Display */}
              <div>
                <div className="text-xs font-semibold text-slate-300 mb-2 flex items-center justify-between">
                  <span>Sanitized Event Metadata</span>
                  <span className="text-[11px] text-emerald-400 font-medium">
                    Secrets Masked
                  </span>
                </div>
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 font-mono text-[11px] text-slate-300 overflow-x-auto">
                  <pre>{JSON.stringify(selectedEvent.safe_metadata, null, 2)}</pre>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
