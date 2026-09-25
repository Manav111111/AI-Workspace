'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import {
  AIEmployee,
  OperationalMetrics,
  Span,
  TraceSummary,
} from '@/types';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Copy,
  Cpu,
  Database,
  Download,
  Filter,
  Layers,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  Terminal,
  Wrench,
  X,
  XCircle,
  Zap,
} from 'lucide-react';

export default function ObservabilityPage() {
  const [traces, setTraces] = useState<TraceSummary[]>([]);
  const [metrics, setMetrics] = useState<OperationalMetrics | null>(null);
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Filters
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('ALL');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  // Selected Trace & Drawer
  const [selectedTrace, setSelectedTrace] = useState<TraceSummary | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null);
  const [copiedTraceId, setCopiedTraceId] = useState(false);
  const [copiedPayload, setCopiedPayload] = useState(false);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [fetchedTraces, fetchedMetrics, fetchedEmployees] = await Promise.all([
        api.listTraces({ limit: 50 }),
        api.getMetricsSummary(),
        api.getAIEmployees(),
      ]);
      setTraces(fetchedTraces);
      setMetrics(fetchedMetrics);
      setEmployees(fetchedEmployees);
    } catch (err) {
      console.error('Failed to load observability data:', err);
    } finally {
      setLoading(false);
    }
  }

  async function refreshData() {
    setRefreshing(true);
    try {
      const [fetchedTraces, fetchedMetrics] = await Promise.all([
        api.listTraces({
          ai_employee_id: selectedEmployeeId !== 'ALL' ? selectedEmployeeId : undefined,
          limit: 50,
        }),
        api.getMetricsSummary(),
      ]);
      setTraces(fetchedTraces);
      setMetrics(fetchedMetrics);
    } catch (err) {
      console.error('Failed to refresh observability data:', err);
    } finally {
      setRefreshing(false);
    }
  }

  async function handleSelectTrace(trace: TraceSummary) {
    try {
      const fullTrace = await api.getTrace(trace.trace_id);
      setSelectedTrace(fullTrace);
      if (fullTrace.spans_data && fullTrace.spans_data.length > 0) {
        setSelectedSpan(fullTrace.spans_data[0]);
      } else {
        setSelectedSpan(null);
      }
    } catch (err) {
      console.error('Failed to fetch full trace:', err);
      setSelectedTrace(trace);
      setSelectedSpan(trace.spans_data?.[0] || null);
    }
  }

  const copyToClipboard = (text: string, isTraceId: boolean = true) => {
    navigator.clipboard.writeText(text);
    if (isTraceId) {
      setCopiedTraceId(true);
      setTimeout(() => setCopiedTraceId(false), 2000);
    } else {
      setCopiedPayload(true);
      setTimeout(() => setCopiedPayload(false), 2000);
    }
  };

  const filteredTraces = useMemo(() => {
    return traces.filter((t) => {
      if (selectedEmployeeId !== 'ALL' && t.ai_employee_id !== selectedEmployeeId) {
        return false;
      }
      if (selectedStatus !== 'ALL' && t.status !== selectedStatus) {
        return false;
      }
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase();
        const matchesTraceId = t.trace_id.toLowerCase().includes(query);
        const matchesReqType = t.request_type.toLowerCase().includes(query);
        const matchesError = t.error_message?.toLowerCase().includes(query);
        if (!matchesTraceId && !matchesReqType && !matchesError) return false;
      }
      return true;
    });
  }, [traces, selectedEmployeeId, selectedStatus, searchQuery]);

  // Color generator for span badges based on operation name
  const getSpanColor = (name: string) => {
    if (name.includes('llm') || name.includes('generate')) {
      return { bg: 'bg-purple-950/40', border: 'border-purple-800/60', text: 'text-purple-400', bar: 'bg-purple-500' };
    }
    if (name.includes('retrieval') || name.includes('qdrant') || name.includes('bm25')) {
      return { bg: 'bg-cyan-950/40', border: 'border-cyan-800/60', text: 'text-cyan-400', bar: 'bg-cyan-500' };
    }
    if (name.includes('tool') || name.includes('action')) {
      return { bg: 'bg-emerald-950/40', border: 'border-emerald-800/60', text: 'text-emerald-400', bar: 'bg-emerald-500' };
    }
    if (name.includes('prompt') || name.includes('assemble')) {
      return { bg: 'bg-amber-950/40', border: 'border-amber-800/60', text: 'text-amber-400', bar: 'bg-amber-500' };
    }
    return { bg: 'bg-indigo-950/40', border: 'border-indigo-800/60', text: 'text-indigo-400', bar: 'bg-indigo-500' };
  };

  const getEmployeeName = (id?: string | null) => {
    if (!id) return 'System / Shared';
    const found = employees.find((e) => e.id === id);
    return found ? found.name : `${id.slice(0, 8)}...`;
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Activity className="w-6 h-6 text-indigo-400 animate-pulse" />
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Distributed Tracing & Telemetry
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30">
              OpenTelemetry Native
            </span>
          </div>
          <p className="text-sm text-slate-400">
            Real-time request trace trees, latency percentiles, breakdown spans, and production audit telemetry.
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

      {/* Operational Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Requests & Success Rate */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Total Throughput</span>
            <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white mb-1">
            {metrics?.requests_total ?? 0}
            <span className="text-xs text-slate-400 font-normal ml-1.5">requests</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <span
              className={`font-semibold flex items-center gap-1 ${
                (metrics?.error_rate_percent ?? 0) === 0
                  ? 'text-emerald-400'
                  : 'text-rose-400'
              }`}
            >
              {metrics?.requests_total ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {((metrics.requests_success / metrics.requests_total) * 100).toFixed(1)}% success
                </>
              ) : (
                '100% healthy'
              )}
            </span>
            <span className="text-slate-500">|</span>
            <span className="text-slate-400">{metrics?.requests_error ?? 0} errors</span>
          </div>
        </div>

        {/* Card 2: P95 Total Latency */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">P95 End-to-End Latency</span>
            <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400 border border-amber-500/20">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white mb-1">
            {metrics?.latencies_ms.total.p95 ?? 0}
            <span className="text-xs text-slate-400 font-normal ml-1">ms</span>
          </div>
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span>Avg: {metrics?.latencies_ms.total.avg ?? 0}ms</span>
            <span className="text-slate-600">•</span>
            <span>P50: {metrics?.latencies_ms.total.p50 ?? 0}ms</span>
          </div>
        </div>

        {/* Card 3: Component Latencies Breakdown */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Avg Subsystem Latency</span>
            <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="flex items-center justify-between">
              <span className="text-purple-400 font-medium flex items-center gap-1">
                <Cpu className="w-3 h-3" /> LLM Generation
              </span>
              <span className="text-slate-200 font-mono">
                {metrics?.latencies_ms.llm.avg ?? 0}ms
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-cyan-400 font-medium flex items-center gap-1">
                <Database className="w-3 h-3" /> Hybrid Retrieval
              </span>
              <span className="text-slate-200 font-mono">
                {metrics?.latencies_ms.retrieval.avg ?? 0}ms
              </span>
            </div>
          </div>
        </div>

        {/* Card 4: Governance Denials */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Governance & Limits</span>
            <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white mb-1">
            {(metrics?.budget_denials_total ?? 0) + (metrics?.rate_limit_denials_total ?? 0)}
            <span className="text-xs text-slate-400 font-normal ml-1.5">blocked</span>
          </div>
          <div className="flex items-center gap-3 text-xs text-slate-400">
            <span>Budget: {metrics?.budget_denials_total ?? 0}</span>
            <span className="text-slate-600">•</span>
            <span>Rate limits: {metrics?.rate_limit_denials_total ?? 0}</span>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-xl border border-slate-800">
        <div className="flex flex-wrap items-center gap-3">
          {/* Employee Filter */}
          <div className="relative">
            <select
              value={selectedEmployeeId}
              onChange={(e) => setSelectedEmployeeId(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-2 pr-8 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All AI Employees</option>
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name}
                </option>
              ))}
            </select>
          </div>

          {/* Status Filter */}
          <div className="relative">
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-2 pr-8 focus:outline-none focus:border-indigo-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="SUCCESS">SUCCESS</option>
              <option value="ERROR">ERROR</option>
            </select>
          </div>
        </div>

        {/* Search input */}
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search trace ID or request type..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg pl-9 pr-3 py-2 focus:outline-none focus:border-indigo-500 placeholder-slate-500"
          />
        </div>
      </div>

      {/* Main Content Area: Traces Table and Trace Detail Modal */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-lg">
        <div className="px-5 py-4 border-b border-slate-800/80 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-semibold text-white">Execution Traces</h2>
            <span className="text-xs text-slate-500">({filteredTraces.length} recorded)</span>
          </div>
          <span className="text-xs text-slate-400">Strict Multi-Tenant Isolated</span>
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
            <RefreshCw className="w-6 h-6 animate-spin text-indigo-400" />
            <p className="text-sm">Loading telemetry trace summaries...</p>
          </div>
        ) : filteredTraces.length === 0 ? (
          <div className="py-16 text-center text-slate-400">
            <Activity className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-300">No traces found</p>
            <p className="text-xs text-slate-500 mt-1">
              Traces are recorded automatically during conversations, playground tests, and agent actions.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/50 text-slate-400 font-medium">
                  <th className="py-3 px-4">Trace ID</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">AI Employee</th>
                  <th className="py-3 px-4">Operation Type</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Spans</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {filteredTraces.map((trace) => {
                  const isErr = trace.status.toUpperCase() === 'ERROR';
                  return (
                    <tr
                      key={trace.id}
                      onClick={() => handleSelectTrace(trace)}
                      className="hover:bg-slate-800/40 cursor-pointer transition"
                    >
                      <td className="py-3 px-4 font-mono font-medium text-indigo-400 flex items-center gap-1.5">
                        <span>{trace.trace_id.slice(0, 16)}...</span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(trace.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })}
                      </td>
                      <td className="py-3 px-4 font-medium text-slate-300">
                        {getEmployeeName(trace.ai_employee_id)}
                      </td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded font-mono text-[11px] bg-slate-800 text-slate-300 border border-slate-700">
                          {trace.request_type}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            isErr
                              ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                              : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                          }`}
                        >
                          {isErr ? (
                            <XCircle className="w-3 h-3" />
                          ) : (
                            <CheckCircle2 className="w-3 h-3" />
                          )}
                          {trace.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        <span className="font-mono">{trace.spans_count}</span> spans
                      </td>
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-medium text-slate-200">
                            {trace.total_latency_ms.toFixed(0)}ms
                          </span>
                          <div className="w-16 h-1.5 bg-slate-800 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-indigo-500 rounded-full"
                              style={{
                                width: `${Math.min(100, (trace.total_latency_ms / 3000) * 100)}%`,
                              }}
                            />
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSelectTrace(trace);
                          }}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-indigo-400 hover:text-indigo-300 transition text-[11px] font-medium"
                        >
                          Inspect Trace
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

      {/* Trace Inspector Drawer / Modal */}
      {selectedTrace && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex justify-end">
          <div className="w-full max-w-4xl bg-slate-950 border-l border-slate-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
            {/* Drawer Header */}
            <div className="p-5 border-b border-slate-800 bg-slate-900/60 flex items-center justify-between">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <Network className="w-5 h-5 text-indigo-400" />
                  <span className="text-sm font-semibold text-white">Trace Explorer</span>
                  <span
                    className={`px-2 py-0.5 text-xs font-semibold rounded-full ${
                      selectedTrace.status === 'ERROR'
                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/30'
                        : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                    }`}
                  >
                    {selectedTrace.status}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                  <span>trace_id: {selectedTrace.trace_id}</span>
                  <button
                    onClick={() => copyToClipboard(selectedTrace.trace_id, true)}
                    className="p-1 hover:text-white transition"
                    title="Copy Trace ID"
                  >
                    {copiedTraceId ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() =>
                    copyToClipboard(JSON.stringify(selectedTrace, null, 2), false)
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
                  onClick={() => setSelectedTrace(null)}
                  className="p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Trace Metadata Strip */}
            <div className="px-5 py-3 border-b border-slate-800/80 bg-slate-900/30 grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
              <div>
                <span className="text-slate-500 block">Total Latency</span>
                <span className="font-mono font-medium text-white">
                  {selectedTrace.total_latency_ms.toFixed(1)} ms
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Total Spans</span>
                <span className="font-mono font-medium text-white">
                  {selectedTrace.spans_count} execution units
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">AI Employee</span>
                <span className="font-medium text-white truncate block">
                  {getEmployeeName(selectedTrace.ai_employee_id)}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block">Timestamp</span>
                <span className="text-slate-300">
                  {new Date(selectedTrace.created_at).toLocaleString()}
                </span>
              </div>
            </div>

            {/* Error banner if trace failed */}
            {selectedTrace.error_message && (
              <div className="m-5 mb-0 p-3 rounded-lg bg-rose-950/30 border border-rose-800/50 flex items-start gap-2.5 text-xs text-rose-300">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-rose-200">Execution Error Recorded</div>
                  <div className="font-mono mt-0.5">{selectedTrace.error_message}</div>
                </div>
              </div>
            )}

            {/* Drawer Body: Two Column (Left: Span Waterfall Tree, Right: Span Detail) */}
            <div className="flex-1 overflow-hidden grid grid-cols-1 md:grid-cols-12">
              {/* Left Column: Span Hierarchy Waterfall */}
              <div className="md:col-span-6 border-r border-slate-800 flex flex-col h-full overflow-hidden">
                <div className="p-3 border-b border-slate-800 bg-slate-900/40 text-xs font-semibold text-slate-300 flex items-center justify-between">
                  <span>Span Execution Waterfall</span>
                  <span className="text-[11px] text-slate-500">Hierarchical Tree</span>
                </div>
                <div className="flex-1 overflow-y-auto p-3 space-y-2">
                  {selectedTrace.spans_data && selectedTrace.spans_data.length > 0 ? (
                    selectedTrace.spans_data.map((span, idx) => {
                      const isSelected = selectedSpan?.span_id === span.span_id;
                      const colors = getSpanColor(span.name);
                      const isChild = !!span.parent_span_id;
                      const spanPct =
                        selectedTrace.total_latency_ms > 0
                          ? Math.min(100, (span.duration_ms / selectedTrace.total_latency_ms) * 100)
                          : 10;

                      return (
                        <div
                          key={span.span_id || idx}
                          onClick={() => setSelectedSpan(span)}
                          className={`p-3 rounded-lg border cursor-pointer transition text-xs ${
                            isSelected
                              ? 'bg-indigo-950/40 border-indigo-500 shadow-md'
                              : 'bg-slate-900/60 border-slate-800/80 hover:border-slate-700'
                          } ${isChild ? 'ml-4 border-l-2' : ''}`}
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <span className={`font-mono font-medium ${colors.text}`}>
                              {span.name}
                            </span>
                            <span className="font-mono text-slate-400">
                              {span.duration_ms.toFixed(1)} ms
                            </span>
                          </div>

                          {/* Relative execution bar */}
                          <div className="w-full bg-slate-950 h-1.5 rounded-full overflow-hidden mb-2">
                            <div
                              className={`h-full ${colors.bar} rounded-full`}
                              style={{ width: `${Math.max(4, spanPct)}%` }}
                            />
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-slate-400">
                            <span className="truncate max-w-[180px]">
                              id: {span.span_id ? span.span_id.slice(0, 10) : 'root'}...
                            </span>
                            <span
                              className={`font-semibold ${
                                span.status === 'ERROR' ? 'text-rose-400' : 'text-emerald-400'
                              }`}
                            >
                              {span.status}
                            </span>
                          </div>
                        </div>
                      );
                    })
                  ) : (
                    <div className="p-8 text-center text-slate-500 text-xs">
                      No nested spans recorded for this trace.
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: Selected Span Attributes & Details */}
              <div className="md:col-span-6 flex flex-col h-full overflow-hidden bg-slate-950">
                <div className="p-3 border-b border-slate-800 bg-slate-900/40 text-xs font-semibold text-slate-300 flex items-center justify-between">
                  <span>Span Attributes & Safe Metadata</span>
                  <span className="text-indigo-400 font-mono text-[11px]">
                    {selectedSpan ? selectedSpan.name : 'Select a span'}
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs">
                  {selectedSpan ? (
                    <>
                      {/* Identity & Duration */}
                      <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Span ID</span>
                          <span className="font-mono text-slate-200">
                            {selectedSpan.span_id || 'N/A'}
                          </span>
                        </div>
                        {selectedSpan.parent_span_id && (
                          <div className="flex items-center justify-between">
                            <span className="text-slate-400">Parent Span ID</span>
                            <span className="font-mono text-slate-200">
                              {selectedSpan.parent_span_id}
                            </span>
                          </div>
                        )}
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Execution Latency</span>
                          <span className="font-mono text-white font-semibold">
                            {selectedSpan.duration_ms.toFixed(2)} ms
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-slate-400">Start Time</span>
                          <span className="font-mono text-slate-400">
                            {selectedSpan.start_time
                              ? new Date(selectedSpan.start_time).toLocaleTimeString()
                              : 'N/A'}
                          </span>
                        </div>
                      </div>

                      {/* Attributes Table */}
                      <div>
                        <div className="text-xs font-semibold text-slate-300 mb-2">
                          Telemetry Attributes (Redacted & Sanitized)
                        </div>
                        {selectedSpan.attributes &&
                        Object.keys(selectedSpan.attributes).length > 0 ? (
                          <div className="border border-slate-800 rounded-lg overflow-hidden">
                            <table className="w-full text-left border-collapse text-[11px]">
                              <tbody className="divide-y divide-slate-800 font-mono">
                                {Object.entries(selectedSpan.attributes).map(([k, v]) => (
                                  <tr key={k} className="hover:bg-slate-900/40">
                                    <td className="py-2 px-3 text-indigo-400 font-medium whitespace-nowrap align-top w-1/3">
                                      {k}
                                    </td>
                                    <td className="py-2 px-3 text-slate-200 break-all">
                                      {typeof v === 'object' ? JSON.stringify(v, null, 2) : String(v)}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <div className="p-4 border border-dashed border-slate-800 rounded-lg text-slate-500 text-center">
                            No custom attributes on this span.
                          </div>
                        )}
                      </div>

                      {/* Events Log */}
                      {selectedSpan.events && selectedSpan.events.length > 0 && (
                        <div>
                          <div className="text-xs font-semibold text-slate-300 mb-2">
                            Span Events & Exceptions
                          </div>
                          <div className="space-y-2">
                            {selectedSpan.events.map((ev, i) => (
                              <div
                                key={i}
                                className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-[11px]"
                              >
                                <div className="flex items-center justify-between font-mono text-amber-400 font-medium mb-1">
                                  <span>{ev.name}</span>
                                  <span className="text-slate-500">{ev.timestamp}</span>
                                </div>
                                {ev.attributes && (
                                  <pre className="text-slate-400 bg-slate-950 p-2 rounded overflow-x-auto">
                                    {JSON.stringify(ev.attributes, null, 2)}
                                  </pre>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="p-8 text-center text-slate-500 text-xs">
                      Select a span from the waterfall to inspect attributes.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
