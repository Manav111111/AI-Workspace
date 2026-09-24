'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import {
  AIEmployee,
  EvaluationBaseline,
  EvaluationResultItem,
  EvaluationRun,
} from '@/types';
import {
  BarChart3,
  Play,
  RotateCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  FileText,
  Clock,
  ChevronRight,
  ShieldCheck,
  Search,
  Filter,
  X,
  Copy,
  Check,
  TrendingUp,
  Cpu,
  Layers,
  ArrowRight,
  Info,
  Award,
} from 'lucide-react';

export default function EvaluationsPage() {
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [baseline, setBaseline] = useState<EvaluationBaseline | null>(null);
  const [selectedRun, setSelectedRun] = useState<EvaluationRun | null>(null);
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningEval, setRunningEval] = useState(false);
  const [evalProgressMsg, setEvalProgressMsg] = useState('');

  // Modals
  const [isRunModalOpen, setIsRunModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [reportMarkdown, setReportMarkdown] = useState('');
  const [reportLoading, setReportLoading] = useState(false);
  const [inspectedItem, setInspectedItem] = useState<EvaluationResultItem | null>(null);
  const [copiedReport, setCopiedReport] = useState(false);

  // New Run Form State
  const [selectedEmployeeId, setSelectedEmployeeId] = useState('');
  const [datasetChoice, setDatasetChoice] = useState<'golden_hr' | 'custom'>('golden_hr');
  const [customJsonl, setCustomJsonl] = useState('');
  const [runGenEval, setRunGenEval] = useState(true);
  const [formError, setFormError] = useState<string | null>(null);

  // Filter / Search for Query Items
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('ALL');

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [fetchedRuns, fetchedBaseline, fetchedEmployees] = await Promise.all([
        api.getEvaluationRuns(),
        api.getEvaluationBaseline(),
        api.getAIEmployees(),
      ]);
      setRuns(fetchedRuns);
      setBaseline(fetchedBaseline);
      setEmployees(fetchedEmployees);

      if (fetchedEmployees.length > 0 && !selectedEmployeeId) {
        setSelectedEmployeeId(fetchedEmployees[0].id);
      }

      if (fetchedRuns.length > 0) {
        // Automatically fetch full details with items for the most recent run
        const fullLatest = await api.getEvaluationRun(fetchedRuns[0].id);
        setSelectedRun(fullLatest);
      }
    } catch (err: any) {
      console.error('Failed to load evaluation data:', err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectRun(runId: string) {
    try {
      const fullRun = await api.getEvaluationRun(runId);
      setSelectedRun(fullRun);
    } catch (err) {
      console.error('Failed to fetch evaluation run details:', err);
    }
  }

  async function handleOpenReport(runId: string) {
    setIsReportModalOpen(true);
    setReportLoading(true);
    try {
      const report = await api.getEvaluationReport(runId);
      setReportMarkdown(report);
    } catch (err: any) {
      setReportMarkdown('Error loading report: ' + (err.message || 'Unknown error'));
    } finally {
      setReportLoading(false);
    }
  }

  async function handleSetBaseline(runId: string) {
    if (!confirm('Promote this evaluation run as the new authoritative baseline for regression checks?')) {
      return;
    }
    try {
      await api.setEvaluationBaseline(runId);
      const updatedBaseline = await api.getEvaluationBaseline();
      setBaseline(updatedBaseline);
      alert('Authoritative baseline updated successfully.');
    } catch (err: any) {
      alert('Failed to set baseline: ' + err.message);
    }
  }

  async function handleStartEvaluation(e: React.FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!selectedEmployeeId) {
      setFormError('Please select an AI Employee to evaluate.');
      return;
    }

    let parsedCustomDataset: any[] | undefined = undefined;
    if (datasetChoice === 'custom') {
      try {
        parsedCustomDataset = customJsonl
          .trim()
          .split('\n')
          .filter((line) => line.trim().length > 0)
          .map((line) => JSON.parse(line));
      } catch (err: any) {
        setFormError('Invalid JSONL format: ' + err.message);
        return;
      }
    }

    setIsRunModalOpen(false);
    setRunningEval(true);
    setEvalProgressMsg('Executing production retrieval and evaluation pipeline against Qdrant...');

    try {
      const newRun = await api.runEvaluation({
        ai_employee_id: selectedEmployeeId,
        dataset_name: datasetChoice === 'golden_hr' ? 'golden_eval_dataset_hr' : 'custom_dataset',
        run_generation_eval: runGenEval,
        custom_dataset: parsedCustomDataset,
      });

      // Reload list and set as selected
      const fullRun = await api.getEvaluationRun(newRun.id);
      setSelectedRun(fullRun);
      setRuns((prev) => [fullRun, ...prev]);

      // Refresh baseline in case this was the initial run
      const freshBaseline = await api.getEvaluationBaseline();
      setBaseline(freshBaseline);
    } catch (err: any) {
      alert('Evaluation failed: ' + (err.message || 'Check backend logs'));
    } finally {
      setRunningEval(false);
      setEvalProgressMsg('');
    }
  }

  // Display metrics either from selected run or baseline
  const activeMetrics = selectedRun?.metrics_summary || baseline?.metrics || {};
  const baselineMetrics = baseline?.metrics || {};

  // Compute regression diffs if selectedRun is evaluated against baseline
  function getMetricDiff(metricKey: string) {
    if (!selectedRun || !baseline || selectedRun.id === baseline.baseline_run_id) return null;
    const curr = selectedRun.metrics_summary?.[metricKey];
    const base = baselineMetrics[metricKey];
    if (curr === undefined || base === undefined) return null;
    const diff = curr - base;
    return diff;
  }

  // Filter items in selected run
  const filteredItems = (selectedRun?.items || []).filter((item) => {
    const matchesSearch =
      searchQuery === '' ||
      item.query_text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.query_id.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      categoryFilter === 'ALL' ||
      (item.category && item.category.toLowerCase() === categoryFilter.toLowerCase());
    return matchesSearch && matchesCategory;
  });

  const categories = Array.from(
    new Set((selectedRun?.items || []).map((it) => it.category).filter(Boolean))
  ) as string[];

  return (
    <div className="max-w-7xl mx-auto space-y-8 pb-16">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <BarChart3 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-white tracking-tight">
                  RAG Evaluation & Benchmarking
                </h1>
                <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Phase 8 Active
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-1">
                Quantitative Information Retrieval & Generation evaluation directly executing the production retrieval pipeline against golden datasets.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            disabled={loading || runningEval}
            className="p-2.5 rounded-lg border border-slate-700 bg-slate-800/80 text-slate-300 hover:text-white hover:bg-slate-700 transition"
            title="Refresh Evaluation Data"
          >
            <RotateCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setIsRunModalOpen(true)}
            disabled={runningEval}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold shadow-lg shadow-indigo-600/30 transition disabled:opacity-50"
          >
            <Play className="w-4 h-4 fill-current" />
            Run Benchmark
          </button>
        </div>
      </div>

      {/* Running Evaluation Banner */}
      {runningEval && (
        <div className="p-4 rounded-xl bg-indigo-950/40 border border-indigo-500/30 flex items-center justify-between animate-pulse">
          <div className="flex items-center gap-3">
            <RotateCw className="w-5 h-5 text-indigo-400 animate-spin" />
            <div>
              <div className="text-sm font-semibold text-indigo-200">
                Running Production RAG Evaluation Benchmark...
              </div>
              <div className="text-xs text-indigo-400 mt-0.5">
                {evalProgressMsg || 'Querying Qdrant vectors and executing LLM-as-a-judge...'}
              </div>
            </div>
          </div>
          <div className="text-xs font-mono text-indigo-300 bg-indigo-900/50 px-3 py-1 rounded-md border border-indigo-700/50">
            Live Execution
          </div>
        </div>
      )}

      {/* Baseline & Regression Policy Banner */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 relative overflow-hidden backdrop-blur-sm">
        <div className="absolute top-0 right-0 w-96 h-96 bg-purple-600/5 rounded-full blur-3xl pointer-events-none" />
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <h2 className="text-base font-semibold text-white">
                Regression Gate & Baseline Policy
              </h2>
              <span className="px-2 py-0.5 text-xs font-mono font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                ACTIVE GATE
              </span>
            </div>
            <p className="text-xs text-slate-400 max-w-2xl leading-relaxed">
              Every production retrieval or prompt modification is strictly measured against the active baseline. CI/CD regression gates reject regressions exceeding{' '}
              <strong className="text-slate-200">5% tolerance</strong> on Recall@5, MRR, or Faithfulness, and enforce a{' '}
              <strong className="text-rose-300">0% tolerance</strong> for hallucinations on negative/out-of-scope queries.
            </p>
          </div>

          <div className="flex items-center gap-4 bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 text-xs">
            <div>
              <div className="text-slate-400 font-medium">Active Baseline ID</div>
              <div className="font-mono text-slate-200 mt-0.5 text-[11px]">
                {baseline?.baseline_run_id ? baseline.baseline_run_id.substring(0, 16) + '...' : 'Not Established Yet'}
              </div>
            </div>
            <div className="h-8 w-px bg-slate-800" />
            <div>
              <div className="text-slate-400 font-medium">Dataset</div>
              <div className="font-medium text-purple-300 mt-0.5">
                {baseline?.dataset_name || 'None'}
              </div>
            </div>
            <div className="h-8 w-px bg-slate-800" />
            <div>
              <div className="text-slate-400 font-medium">Status</div>
              <div className="flex items-center gap-1.5 text-emerald-400 font-medium mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Protected
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards: Pure IR & Generation Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-4">
        {/* Recall@5 */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Recall@5</span>
            <TrendingUp className="w-3.5 h-3.5 text-indigo-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white">
              {activeMetrics.recall_at_5 !== undefined
                ? (activeMetrics.recall_at_5 * 100).toFixed(1) + '%'
                : '—'}
            </div>
            {getMetricDiff('recall_at_5') !== null && (
              <div
                className={`text-[10px] mt-1 font-semibold flex items-center gap-1 ${
                  getMetricDiff('recall_at_5')! >= 0
                    ? 'text-emerald-400'
                    : getMetricDiff('recall_at_5')! > -0.05
                    ? 'text-amber-400'
                    : 'text-rose-400'
                }`}
              >
                {getMetricDiff('recall_at_5')! >= 0 ? '+' : ''}
                {(getMetricDiff('recall_at_5')! * 100).toFixed(1)}% vs base
              </div>
            )}
            <div className="text-[10px] text-slate-500 mt-1">Hits in top 5 chunks</div>
          </div>
        </div>

        {/* Recall@1 */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Recall@1</span>
            <Award className="w-3.5 h-3.5 text-blue-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white">
              {activeMetrics.recall_at_1 !== undefined
                ? (activeMetrics.recall_at_1 * 100).toFixed(1) + '%'
                : '—'}
            </div>
            {getMetricDiff('recall_at_1') !== null && (
              <div
                className={`text-[10px] mt-1 font-semibold ${
                  getMetricDiff('recall_at_1')! >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {getMetricDiff('recall_at_1')! >= 0 ? '+' : ''}
                {(getMetricDiff('recall_at_1')! * 100).toFixed(1)}% vs base
              </div>
            )}
            <div className="text-[10px] text-slate-500 mt-1">Top-1 rank accuracy</div>
          </div>
        </div>

        {/* MRR */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">MRR</span>
            <Layers className="w-3.5 h-3.5 text-purple-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white">
              {activeMetrics.mrr !== undefined ? activeMetrics.mrr.toFixed(3) : '—'}
            </div>
            {getMetricDiff('mrr') !== null && (
              <div
                className={`text-[10px] mt-1 font-semibold ${
                  getMetricDiff('mrr')! >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {getMetricDiff('mrr')! >= 0 ? '+' : ''}
                {getMetricDiff('mrr')!.toFixed(3)} vs base
              </div>
            )}
            <div className="text-[10px] text-slate-500 mt-1">Mean Reciprocal Rank</div>
          </div>
        </div>

        {/* NDCG@5 */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">NDCG@5</span>
            <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white">
              {activeMetrics.ndcg_at_5 !== undefined ? activeMetrics.ndcg_at_5.toFixed(3) : '—'}
            </div>
            {getMetricDiff('ndcg_at_5') !== null && (
              <div
                className={`text-[10px] mt-1 font-semibold ${
                  getMetricDiff('ndcg_at_5')! >= 0 ? 'text-emerald-400' : 'text-rose-400'
                }`}
              >
                {getMetricDiff('ndcg_at_5')! >= 0 ? '+' : ''}
                {getMetricDiff('ndcg_at_5')!.toFixed(3)} vs base
              </div>
            )}
            <div className="text-[10px] text-slate-500 mt-1">Discounted Cum. Gain</div>
          </div>
        </div>

        {/* Faithfulness */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Faithfulness</span>
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white">
              {activeMetrics.faithfulness !== undefined
                ? (activeMetrics.faithfulness * 100).toFixed(1) + '%'
                : '—'}
            </div>
            <div className="text-[10px] text-slate-500 mt-1">LLM groundedness judge</div>
          </div>
        </div>

        {/* Answer Relevance */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Relevance</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-teal-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white">
              {activeMetrics.answer_relevance !== undefined
                ? (activeMetrics.answer_relevance * 100).toFixed(1) + '%'
                : '—'}
            </div>
            <div className="text-[10px] text-slate-500 mt-1">Semantic overlap score</div>
          </div>
        </div>

        {/* Avg Latency */}
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Latency</span>
            <Clock className="w-3.5 h-3.5 text-amber-400" />
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white">
              {activeMetrics.avg_total_latency_ms !== undefined
                ? Math.round(activeMetrics.avg_total_latency_ms) + 'ms'
                : '—'}
            </div>
            <div className="text-[10px] text-slate-500 mt-1">Retrieval + generation</div>
          </div>
        </div>
      </div>

      {/* Past Runs Table & Run Selector */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-white">Evaluation Runs History</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Historical benchmark executions and baseline tracking.
            </p>
          </div>
          <div className="text-xs text-slate-400">
            Total Runs: <span className="text-white font-semibold">{runs.length}</span>
          </div>
        </div>

        {runs.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No evaluation runs recorded yet. Click &ldquo;Run Benchmark&rdquo; to execute the initial run.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider border-b border-slate-800 font-semibold text-[10px]">
                <tr>
                  <th className="py-3 px-4">Run ID / Dataset</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Recall@5</th>
                  <th className="py-3 px-4">Recall@1</th>
                  <th className="py-3 px-4">MRR</th>
                  <th className="py-3 px-4">NDCG@5</th>
                  <th className="py-3 px-4">Faithfulness</th>
                  <th className="py-3 px-4">Queries</th>
                  <th className="py-3 px-4">Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {runs.map((run) => {
                  const isSelected = selectedRun?.id === run.id;
                  const isBaseline = baseline?.baseline_run_id === run.id;
                  const m = run.metrics_summary || {};
                  return (
                    <tr
                      key={run.id}
                      onClick={() => handleSelectRun(run.id)}
                      className={`cursor-pointer transition hover:bg-slate-800/40 ${
                        isSelected ? 'bg-indigo-600/10 border-l-2 border-indigo-500' : ''
                      }`}
                    >
                      <td className="py-3.5 px-4 font-mono">
                        <div className="flex items-center gap-2">
                          <span className="text-white font-medium">
                            {run.id.substring(0, 8)}...
                          </span>
                          {isBaseline && (
                            <span className="px-1.5 py-0.5 text-[9px] font-sans font-semibold rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                              BASELINE
                            </span>
                          )}
                        </div>
                        <div className="text-[10px] text-slate-400 font-sans mt-0.5">
                          {run.dataset_name}
                        </div>
                      </td>
                      <td className="py-3.5 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            run.status === 'COMPLETED'
                              ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              : run.status === 'RUNNING'
                              ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                              : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          }`}
                        >
                          {run.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 font-semibold text-white">
                        {m.recall_at_5 !== undefined ? (m.recall_at_5 * 100).toFixed(1) + '%' : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-slate-300">
                        {m.recall_at_1 !== undefined ? (m.recall_at_1 * 100).toFixed(1) + '%' : '—'}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-purple-300">
                        {m.mrr !== undefined ? m.mrr.toFixed(3) : '—'}
                      </td>
                      <td className="py-3.5 px-4 font-mono text-cyan-300">
                        {m.ndcg_at_5 !== undefined ? m.ndcg_at_5.toFixed(3) : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-emerald-400 font-medium">
                        {m.faithfulness !== undefined ? (m.faithfulness * 100).toFixed(1) + '%' : '—'}
                      </td>
                      <td className="py-3.5 px-4 text-slate-400">{run.total_queries}</td>
                      <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                        {new Date(run.created_at).toLocaleDateString()}{' '}
                        {new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </td>
                      <td className="py-3.5 px-4 text-right space-x-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenReport(run.id);
                          }}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-medium transition"
                          title="View Markdown Report"
                        >
                          Report
                        </button>
                        {!isBaseline && run.status === 'COMPLETED' && (
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              handleSetBaseline(run.id);
                            }}
                            className="px-2.5 py-1 rounded bg-purple-950/60 hover:bg-purple-900 border border-purple-800/60 text-purple-300 text-[11px] font-medium transition"
                            title="Set as authoritative baseline"
                          >
                            Set Baseline
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Query Breakdown Table for Selected Run */}
      {selectedRun && (
        <div className="bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden space-y-4">
          <div className="p-5 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-white">
                  Query Performance Breakdown
                </h3>
                <span className="text-xs font-mono text-indigo-400 bg-indigo-950/50 border border-indigo-800/40 px-2 py-0.5 rounded">
                  Run: {selectedRun.id.substring(0, 8)}
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Per-query breakdown of retrieved chunks, rankings, reciprocal ranks, and faithfulness scores.
              </p>
            </div>

            {/* Filters */}
            <div className="flex items-center gap-3">
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                <input
                  type="text"
                  placeholder="Search queries..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-8 pr-3 py-1.5 bg-slate-950/80 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="px-3 py-1.5 bg-slate-950/80 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="ALL">All Categories</option>
                {categories.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-950/60 text-slate-400 uppercase tracking-wider border-b border-slate-800 font-semibold text-[10px]">
                <tr>
                  <th className="py-3 px-4">Query ID / Category</th>
                  <th className="py-3 px-4">Query Text</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Recall@5</th>
                  <th className="py-3 px-4">Precision@5</th>
                  <th className="py-3 px-4">Reciprocal Rank</th>
                  <th className="py-3 px-4">Faithfulness</th>
                  <th className="py-3 px-4">Relevance</th>
                  <th className="py-3 px-4">Latency</th>
                  <th className="py-3 px-4 text-right">Inspect</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {filteredItems.map((item) => {
                  const hit = (item.recall_at_5 || 0) > 0;
                  return (
                    <tr
                      key={item.id}
                      className="hover:bg-slate-800/30 transition cursor-pointer"
                      onClick={() => setInspectedItem(item)}
                    >
                      <td className="py-3 px-4 font-mono">
                        <span className="text-white font-medium">{item.query_id}</span>
                        {item.category && (
                          <div className="text-[10px] text-purple-400 font-sans">{item.category}</div>
                        )}
                      </td>
                      <td className="py-3 px-4 max-w-xs truncate text-slate-200 font-medium">
                        {item.query_text}
                      </td>
                      <td className="py-3 px-4">
                        {item.is_answerable ? (
                          <span className="px-2 py-0.5 rounded text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/20 font-medium">
                            Answerable
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-400 border border-amber-500/20 font-medium">
                            Negative
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4">
                        {item.is_answerable ? (
                          <span
                            className={`font-semibold ${
                              hit ? 'text-emerald-400' : 'text-rose-400'
                            }`}
                          >
                            {((item.recall_at_5 || 0) * 100).toFixed(0)}%
                          </span>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {item.is_answerable && item.precision_at_5 !== undefined && item.precision_at_5 !== null
                          ? ((item.precision_at_5 || 0) * 100).toFixed(0) + '%'
                          : '—'}
                      </td>
                      <td className="py-3 px-4 font-mono text-purple-300">
                        {item.is_answerable && item.reciprocal_rank !== undefined && item.reciprocal_rank !== null
                          ? item.reciprocal_rank.toFixed(2)
                          : '—'}
                      </td>
                      <td className="py-3 px-4 font-medium text-emerald-400">
                        {item.faithfulness_score !== undefined && item.faithfulness_score !== null
                          ? (item.faithfulness_score * 100).toFixed(0) + '%'
                          : '—'}
                      </td>
                      <td className="py-3 px-4 text-teal-400">
                        {item.answer_relevance_score !== undefined && item.answer_relevance_score !== null
                          ? (item.answer_relevance_score * 100).toFixed(0) + '%'
                          : item.refusal_correct
                          ? 'Refused (OK)'
                          : '—'}
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-[11px]">
                        {item.total_latency_ms ? Math.round(item.total_latency_ms) + 'ms' : '—'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setInspectedItem(item);
                          }}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-medium transition"
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* RUN BENCHMARK MODAL */}
      {isRunModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-xl p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
              <div>
                <h3 className="text-lg font-bold text-white">Execute RAG Evaluation Benchmark</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Executes the exact production RetrievalService against selected test dataset.
                </p>
              </div>
              <button
                onClick={() => setIsRunModalOpen(false)}
                className="p-1 rounded text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-400 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleStartEvaluation} className="space-y-4">
              {/* Select AI Employee */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Target AI Employee (Production KB Scoping)
                </label>
                <select
                  value={selectedEmployeeId}
                  onChange={(e) => setSelectedEmployeeId(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-sm text-slate-200 focus:outline-none focus:border-indigo-500"
                >
                  {employees.map((emp) => (
                    <option key={emp.id} value={emp.id}>
                      {emp.name} — {emp.role}
                    </option>
                  ))}
                </select>
                <span className="text-[11px] text-slate-500 mt-1 block">
                  The evaluation runner strictly loads this employee&apos;s assigned knowledge bases and tenant scope.
                </span>
              </div>

              {/* Dataset Choice */}
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Evaluation Dataset
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setDatasetChoice('golden_hr')}
                    className={`p-3 rounded-lg border text-left transition ${
                      datasetChoice === 'golden_hr'
                        ? 'bg-indigo-600/15 border-indigo-500/50 text-white'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <div className="font-semibold text-xs text-slate-200">Default Golden HR Dataset</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      20 curated queries (15 positive policies + 5 negative out-of-scope)
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setDatasetChoice('custom')}
                    className={`p-3 rounded-lg border text-left transition ${
                      datasetChoice === 'custom'
                        ? 'bg-indigo-600/15 border-indigo-500/50 text-white'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    <div className="font-semibold text-xs text-slate-200">Custom JSONL Dataset</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Provide ad-hoc evaluation queries in JSON Lines format
                    </div>
                  </button>
                </div>
              </div>

              {/* Custom JSONL input */}
              {datasetChoice === 'custom' && (
                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                    Custom Dataset JSON Lines
                  </label>
                  <textarea
                    rows={4}
                    value={customJsonl}
                    onChange={(e) => setCustomJsonl(e.target.value)}
                    placeholder={'{"id": "q1", "query": "What is...", "expected_chunk_ids": ["c1"], "answerable": true}'}
                    className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
                  />
                </div>
              )}

              {/* Toggle Generation Eval */}
              <div className="flex items-center gap-3 pt-2">
                <input
                  type="checkbox"
                  id="runGenEval"
                  checked={runGenEval}
                  onChange={(e) => setRunGenEval(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-0"
                />
                <label htmlFor="runGenEval" className="text-xs text-slate-300 cursor-pointer">
                  Run Generation Evaluation (LLM-as-a-judge for Faithfulness, Relevance, and Refusals)
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsRunModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="inline-flex items-center gap-2 px-5 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-600/30 transition"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  Start Evaluation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MARKDOWN REPORT MODAL */}
      {isReportModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-purple-400" />
                <h3 className="text-base font-bold text-white">Evaluation Benchmark Report</h3>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(reportMarkdown);
                    setCopiedReport(true);
                    setTimeout(() => setCopiedReport(false), 2000);
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
                >
                  {copiedReport ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedReport ? 'Copied!' : 'Copy Markdown'}
                </button>
                <button
                  onClick={() => setIsReportModalOpen(false)}
                  className="p-1 rounded text-slate-400 hover:text-white"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            <div className="p-6 overflow-y-auto flex-1 font-mono text-xs text-slate-300 whitespace-pre-wrap leading-relaxed bg-slate-950/60">
              {reportLoading ? (
                <div className="flex items-center justify-center py-12 text-slate-500">
                  <RotateCw className="w-5 h-5 animate-spin mr-2" />
                  Loading markdown report...
                </div>
              ) : (
                reportMarkdown
              )}
            </div>
          </div>
        </div>
      )}

      {/* QUERY INSPECTION DRAWER / MODAL */}
      {inspectedItem && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded font-semibold">
                    {inspectedItem.query_id}
                  </span>
                  <span className="text-xs text-slate-400">
                    Category: <strong className="text-slate-200">{inspectedItem.category || 'N/A'}</strong>
                  </span>
                </div>
                <h4 className="text-sm font-bold text-white mt-1.5">
                  {inspectedItem.query_text}
                </h4>
              </div>
              <button
                onClick={() => setInspectedItem(null)}
                className="p-1 rounded text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-5 text-xs text-slate-300">
              {/* Metrics summary */}
              <div className="grid grid-cols-4 gap-3 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
                <div>
                  <div className="text-slate-400 font-medium">Recall@5</div>
                  <div className="text-base font-bold text-white mt-0.5">
                    {inspectedItem.recall_at_5 !== undefined && inspectedItem.recall_at_5 !== null
                      ? ((inspectedItem.recall_at_5 || 0) * 100).toFixed(0) + '%'
                      : '—'}
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 font-medium">Reciprocal Rank</div>
                  <div className="text-base font-bold text-purple-300 mt-0.5">
                    {inspectedItem.reciprocal_rank !== undefined && inspectedItem.reciprocal_rank !== null
                      ? inspectedItem.reciprocal_rank.toFixed(2)
                      : '—'}
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 font-medium">Faithfulness</div>
                  <div className="text-base font-bold text-emerald-400 mt-0.5">
                    {inspectedItem.faithfulness_score !== undefined && inspectedItem.faithfulness_score !== null
                      ? (inspectedItem.faithfulness_score * 100).toFixed(0) + '%'
                      : '—'}
                  </div>
                </div>
                <div>
                  <div className="text-slate-400 font-medium">Latency</div>
                  <div className="text-base font-bold text-amber-300 mt-0.5">
                    {inspectedItem.total_latency_ms ? Math.round(inspectedItem.total_latency_ms) + 'ms' : '—'}
                  </div>
                </div>
              </div>

              {/* Expected vs Retrieved Chunks */}
              <div className="space-y-2">
                <div className="font-semibold text-slate-200">Expected Chunk IDs (Ground Truth):</div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-400">
                  {inspectedItem.expected_chunk_ids.length > 0
                    ? inspectedItem.expected_chunk_ids.join('\n')
                    : 'None (Unanswerable / negative query)'}
                </div>
              </div>

              <div className="space-y-2">
                <div className="font-semibold text-slate-200">Retrieved Chunk IDs & Similarity Scores:</div>
                <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 font-mono text-[11px] text-slate-300 space-y-1">
                  {inspectedItem.retrieved_chunk_ids.length > 0 ? (
                    inspectedItem.retrieved_chunk_ids.map((cid, idx) => (
                      <div key={cid} className="flex items-center justify-between">
                        <span>
                          [{idx + 1}] {cid}
                        </span>
                        <span className="text-indigo-400 font-semibold">
                          Score: {inspectedItem.retrieved_scores?.[idx]?.toFixed(4) || '—'}
                        </span>
                      </div>
                    ))
                  ) : (
                    <div className="text-slate-500">Zero chunks retrieved (Refused)</div>
                  )}
                </div>
              </div>

              {/* Generated Answer */}
              {inspectedItem.generated_answer && (
                <div className="space-y-2">
                  <div className="font-semibold text-slate-200">Generated Answer (Production LLM):</div>
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-slate-300 leading-relaxed">
                    {inspectedItem.generated_answer}
                  </div>
                </div>
              )}

              {/* Reference Answer */}
              {inspectedItem.reference_answer && (
                <div className="space-y-2">
                  <div className="font-semibold text-slate-200">Reference Ground Truth Answer:</div>
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-emerald-300 leading-relaxed">
                    {inspectedItem.reference_answer}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
