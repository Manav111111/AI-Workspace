'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import { AuditEvent } from '@/types';
import {
  Lock,
  RefreshCw,
  Search,
  ShieldCheck,
  X,
} from 'lucide-react';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

export default function AuditPage() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Filters
  const [selectedEventType, setSelectedEventType] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Event & Drawer
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);

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

  const getEventBadgeVariant = (eventType: string): 'orange' | 'amber' | 'rose' | 'forest' | 'neutral' => {
    const t = eventType.toUpperCase();
    if (t.includes('EXCEEDED') || t.includes('FAIL') || t.includes('DENIED')) return 'rose';
    if (t.includes('TOOL') || t.includes('ACTION')) return 'orange';
    if (t.includes('BUDGET') || t.includes('OVERRIDE')) return 'amber';
    if (t.includes('AUTH') || t.includes('LOGIN')) return 'neutral';
    return 'neutral';
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <PageHeader
        title="Enterprise Audit Trail"
        description="Tamper-evident operational audit logs, policy mutations, tool executions, and security governance events with automated PII redaction."
        badge={<Badge variant="orange">Append-Only Immutable</Badge>}
        actions={
          <Button
            variant="secondary"
            size="sm"
            icon={RefreshCw}
            loading={refreshing}
            onClick={refreshData}
          >
            Refresh
          </Button>
        }
      />

      {/* Compliance Guarantee Banner */}
      <Card>
        <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#151515] border border-[#262626] text-[#FF9D00]">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="font-semibold text-[#F5F5F5] font-display">
                Automated Redaction & Isolation Guarantees
              </div>
              <div className="text-[#A1A1AA] mt-0.5">
                All payload metadata is stripped of API keys, bearer tokens, passwords, and sensitive PII prior to persistence.
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 font-mono text-[11px] text-[#737373]">
            <Badge variant="neutral">Retention: 365 Days</Badge>
            <Badge variant="orange">Tenant Isolated</Badge>
          </div>
        </CardContent>
      </Card>

      {/* Search and Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#737373]" />
              <input
                type="text"
                placeholder="Filter by Actor, Resource ID, or Trace Context..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-[#0B0B0B] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] placeholder-[#737373] focus:outline-none focus:border-[#FF9D00]"
              />
            </div>

            <select
              value={selectedEventType}
              onChange={(e) => setSelectedEventType(e.target.value)}
              className="bg-[#0B0B0B] border border-[#262626] rounded-lg px-3 py-2 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#FF9D00]"
            >
              <option value="ALL">All Event Types</option>
              <option value="TOOL_EXECUTION">Tool Execution</option>
              <option value="BUDGET_EXCEEDED">Budget Exceeded</option>
              <option value="KNOWLEDGE_INGESTION">Knowledge Ingestion</option>
              <option value="EMPLOYEE_MUTATION">AI Employee Mutation</option>
              <option value="AUTH_SESSION">Auth & Session</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Audit Events Table */}
      <Card>
        <CardHeader>
          <CardTitle subtitle="Chronological immutable events recorded in the audit ledger">
            <span>Recorded Audit Events ({filteredEvents.length})</span>
          </CardTitle>
        </CardHeader>

        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#262626] bg-[#0B0B0B] text-[11px] font-mono text-[#737373] uppercase tracking-wider">
                  <th className="py-3 px-4">Event Type</th>
                  <th className="py-3 px-4">Resource Target</th>
                  <th className="py-3 px-4">Actor</th>
                  <th className="py-3 px-4">Trace ID</th>
                  <th className="py-3 px-4 text-right">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#262626] font-mono text-[11px]">
                {loading ? (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-[#737373] font-sans">
                      Loading audit events...
                    </td>
                  </tr>
                ) : filteredEvents.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-10 text-center text-[#737373] font-sans">
                      No audit events recorded for this query.
                    </td>
                  </tr>
                ) : (
                  filteredEvents.map((evt) => (
                    <tr
                      key={evt.id}
                      onClick={() => setSelectedEvent(evt)}
                      className="hover:bg-[#151515]/60 cursor-pointer transition-colors group"
                    >
                      <td className="py-3 px-4 font-sans">
                        <Badge variant={getEventBadgeVariant(evt.event_type)}>
                          {evt.event_type}
                        </Badge>
                      </td>
                      <td className="py-3 px-4 text-[#F5F5F5] font-medium font-sans">
                        {evt.resource_type}: <span className="font-mono text-[#737373] font-normal">{evt.resource_id?.slice(0, 8)}...</span>
                      </td>
                      <td className="py-3 px-4 text-[#A1A1AA] font-sans">
                        {evt.actor_id ? `Actor #${evt.actor_id.slice(0, 6)}` : 'System Runtime'}
                      </td>
                      <td className="py-3 px-4 text-[#FF9D00]">
                        {evt.trace_id ? `${evt.trace_id.slice(0, 12)}...` : 'N/A'}
                      </td>
                      <td className="py-3 px-4 text-right text-[#737373]">
                        {new Date(evt.created_at).toLocaleString([], {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Audit Event Detail Modal */}
      {selectedEvent && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-2xl p-6 shadow-2xl max-h-[85vh] flex flex-col space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262626] shrink-0">
              <div className="flex items-center gap-2">
                <Lock className="w-4 h-4 text-[#FF9D00]" />
                <h3 className="text-sm font-semibold font-display text-[#F5F5F5]">
                  Audit Event Details: {selectedEvent.event_type}
                </h3>
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="text-[#737373] hover:text-[#F5F5F5] p-1 rounded hover:bg-[#1A1A1A]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs text-[#A1A1AA] flex-1 overflow-y-auto pr-1">
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-[#0B0B0B] rounded-lg border border-[#262626] font-mono text-[11px]">
                  <div className="text-[#737373] font-sans mb-0.5">Event ID:</div>
                  <div className="text-[#F5F5F5] truncate">{selectedEvent.id}</div>
                </div>
                <div className="p-3 bg-[#0B0B0B] rounded-lg border border-[#262626] font-mono text-[11px]">
                  <div className="text-[#737373] font-sans mb-0.5">Trace Context:</div>
                  <div className="text-[#FF9D00] truncate">{selectedEvent.trace_id || 'None'}</div>
                </div>
              </div>

              <div>
                <strong className="block text-[#737373] font-mono text-[11px] mb-1 font-sans">Audit Metadata (PII Redacted):</strong>
                <pre className="p-3 bg-[#050505] rounded-lg border border-[#262626] font-mono text-[11px] text-[#D4D4D8] leading-relaxed max-h-56 overflow-y-auto">
                  {JSON.stringify(selectedEvent.safe_metadata || (selectedEvent as any).metadata || {}, null, 2)}
                </pre>
              </div>
            </div>

            <div className="pt-3 border-t border-[#262626] flex justify-end shrink-0">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setSelectedEvent(null)}
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
