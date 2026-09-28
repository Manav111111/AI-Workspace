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
  FileText,
  Clock,
  ChevronRight,
  Search,
  X,
  Copy,
  Check,
  Award,
} from 'lucide-react';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

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

  const formatPct = (val?: number | null) => (val != null ? `${(val * 100).toFixed(1)}%` : 'N/A');
  const formatNum = (val?: number | null, decimals = 3) => (val != null ? val.toFixed(decimals) : 'N/A');
  const formatMs = (val?: number | null) => (val != null ? `${val.toFixed(0)} ms` : 'N/A');

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
      await loadData();
    } catch (err: any) {
      alert('Failed to set baseline: ' + (err.message || 'Error'));
    }
  }

  async function handleExecuteRun(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedEmployeeId) {
      setFormError('Please select an AI Employee');
      return;
    }

    setRunningEval(true);
    setFormError(null);
    setEvalProgressMsg('Initializing evaluation dataset and pipeline...');

    try {
      let customDataset: any[] | undefined = undefined;
      if (datasetChoice === 'custom') {
        if (!customJsonl.trim()) {
          throw new Error('Please paste custom JSONL dataset items');
        }
        customDataset = customJsonl
          .trim()
          .split('\n')
          .filter(Boolean)
          .map((line, idx) => {
            try {
              return JSON.parse(line);
            } catch (e) {
              throw new Error(`Invalid JSON on line ${idx + 1}`);
            }
          });
      }

      setEvalProgressMsg('Running retrieval benchmark queries across Qdrant & BM25...');

      const newRun = await api.runEvaluation({
        ai_employee_id: selectedEmployeeId,
        dataset_name: datasetChoice === 'golden_hr' ? 'golden_hr_eval' : 'custom_dataset',
        custom_dataset: customDataset,
        run_generation_eval: runGenEval,
      });

      setIsRunModalOpen(false);
      setEvalProgressMsg('');
      await loadData();
      await handleSelectRun(newRun.id);
    } catch (err: any) {
      setFormError(err.message || 'Evaluation run failed');
    } finally {
      setRunningEval(false);
      setEvalProgressMsg('');
    }
  }

  const filteredItems = selectedRun?.items?.filter((item) => {
    const query = item.query_text || (item as any).query || '';
    const matchesSearch =
      searchQuery === '' ||
      query.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (item.category && item.category.toLowerCase().includes(searchQuery.toLowerCase()));
    const matchesCategory =
      categoryFilter === 'ALL' || item.category === categoryFilter;
    return matchesSearch && matchesCategory;
  }) || [];

  const categories = Array.from(
    new Set(selectedRun?.items?.map((i) => i.category).filter(Boolean) as string[])
  );

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <PageHeader
        title="RAG Evaluation & Benchmarking"
        description="Objective accuracy measurement system evaluating Recall@K, Precision@K, MRR, NDCG, refusal accuracy, and automated regression gates."
        badge={<Badge variant="orange">Objective Benchmark Engine</Badge>}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              icon={RotateCw}
              onClick={loadData}
              disabled={loading}
            >
              Refresh
            </Button>
            <Button
              variant="orange"
              size="sm"
              icon={Play}
              onClick={() => setIsRunModalOpen(true)}
            >
              Run Benchmark Evaluation
            </Button>
          </div>
        }
      />

      {/* Main Content Layout */}
      {loading ? (
        <div className="py-24 text-center text-xs text-[#737373] font-mono">
          Loading evaluation runs and baseline telemetry...
        </div>
      ) : runs.length === 0 ? (
        <Card className="p-12 text-center border-dashed border-[#262626] bg-[#101010]">
          <div className="w-12 h-12 rounded-xl bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] mx-auto mb-4 shadow-sm">
            <BarChart3 className="w-6 h-6" />
          </div>
          <h3 className="text-sm font-semibold font-display text-[#F5F5F5]">No Evaluation Runs Found</h3>
          <p className="text-xs text-[#A1A1AA] mt-1 max-w-md mx-auto leading-relaxed">
            Execute your first RAG evaluation run against the Golden HR dataset to compute grounded retrieval metrics.
          </p>
          <Button
            variant="orange"
            size="sm"
            className="mt-5"
            icon={Play}
            onClick={() => setIsRunModalOpen(true)}
          >
            Launch Evaluation Benchmark
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* LEFT SIDEBAR: History of Evaluation Runs */}
          <div className="lg:col-span-1 space-y-3">
            <h2 className="text-[11px] font-mono uppercase tracking-wider text-[#737373] px-1">
              Evaluation Runs ({runs.length})
            </h2>

            <div className="space-y-2 max-h-[70vh] overflow-y-auto pr-1">
              {runs.map((r) => {
                const isSelected = selectedRun?.id === r.id;
                const isBase = baseline?.baseline_run_id === r.id;
                const hasPassed = r.regression_passed;

                return (
                  <div
                    key={r.id}
                    onClick={() => handleSelectRun(r.id)}
                    className={`p-3.5 rounded-lg border cursor-pointer transition-all flex flex-col gap-2 ${
                      isSelected
                        ? 'bg-[#151515] border-[#FF9D00]/40 shadow-sm'
                        : 'bg-[#101010] border-[#262626] hover:bg-[#151515] hover:border-[#333333]'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-1">
                      <span className="text-xs font-semibold font-display text-[#F5F5F5] truncate">
                        {r.dataset_name}
                      </span>
                      <div className="flex items-center gap-1 shrink-0">
                        {isBase && (
                          <Badge variant="amber">Baseline</Badge>
                        )}
                        <Badge variant={hasPassed ? 'forest' : 'rose'} dot>
                          {hasPassed ? 'PASS' : 'FAIL'}
                        </Badge>
                      </div>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-[#737373] font-mono">
                      <span>R@5: <strong className="text-[#FF9D00]">{formatPct(r.recall_at_5)}</strong></span>
                      <span>MRR: <strong className="text-[#F5F5F5]">{formatNum(r.mrr)}</strong></span>
                    </div>

                    <div className="text-[10px] text-[#737373] flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3" />
                      <span>{new Date(r.created_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* RIGHT MAIN PANEL: Active Evaluation Details */}
          <div className="lg:col-span-3 space-y-6">
            {selectedRun && (
              <>
                {/* Run Overview Header Card */}
                <Card>
                  <CardHeader>
                    <div>
                      <div className="flex items-center gap-2.5">
                        <h2 className="text-sm font-semibold font-display text-[#F5F5F5]">
                          Evaluation Benchmark: {selectedRun.dataset_name}
                        </h2>
                        {baseline?.baseline_run_id === selectedRun.id && (
                          <Badge variant="amber">Active Baseline</Badge>
                        )}
                        <Badge variant={selectedRun.regression_passed ? 'forest' : 'rose'} dot>
                          {selectedRun.regression_passed ? 'Regression Gate Passed' : 'Regression Gate Failed'}
                        </Badge>
                      </div>
                      <p className="text-xs text-[#737373] mt-1 font-mono">
                        Target AI Employee: {selectedRun.ai_employee?.name || selectedRun.ai_employee_id} &bull; Total Queries: {selectedRun.total_queries}
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="secondary"
                        size="sm"
                        icon={FileText}
                        onClick={() => handleOpenReport(selectedRun.id)}
                      >
                        Report
                      </Button>
                      {baseline?.baseline_run_id !== selectedRun.id && (
                        <Button
                          variant="secondary"
                          size="sm"
                          icon={Award}
                          onClick={() => handleSetBaseline(selectedRun.id)}
                        >
                          Set Baseline
                        </Button>
                      )}
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    {/* Primary Metrics Grid */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="p-3.5 rounded-lg bg-[#0B0B0B] border border-[#262626]">
                        <div className="text-[11px] text-[#737373] font-mono">Recall@3</div>
                        <div className="text-lg font-bold text-[#F5F5F5] font-mono mt-1">
                          {formatPct(selectedRun.recall_at_3)}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-[#0B0B0B] border border-[#262626]">
                        <div className="text-[11px] text-[#737373] font-mono">Recall@5</div>
                        <div className="text-lg font-bold text-[#FF9D00] font-mono mt-1">
                          {formatPct(selectedRun.recall_at_5)}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-[#0B0B0B] border border-[#262626]">
                        <div className="text-[11px] text-[#737373] font-mono">MRR (Mean Reciprocal)</div>
                        <div className="text-lg font-bold text-[#FFC247] font-mono mt-1">
                          {formatNum(selectedRun.mrr)}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-[#0B0B0B] border border-[#262626]">
                        <div className="text-[11px] text-[#737373] font-mono">NDCG@5</div>
                        <div className="text-lg font-bold text-[#F5F5F5] font-mono mt-1">
                          {formatNum(selectedRun.ndcg_at_5)}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-[#0B0B0B] border border-[#262626]">
                        <div className="text-[11px] text-[#737373] font-mono">Precision@5</div>
                        <div className="text-lg font-bold text-[#F5F5F5] font-mono mt-1">
                          {formatPct(selectedRun.precision_at_5)}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-[#0B0B0B] border border-[#262626]">
                        <div className="text-[11px] text-[#737373] font-mono">Refusal Accuracy</div>
                        <div className="text-lg font-bold text-emerald-400 font-mono mt-1">
                          {formatPct(selectedRun.refusal_accuracy)}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-[#0B0B0B] border border-[#262626]">
                        <div className="text-[11px] text-[#737373] font-mono">Answer Relevance</div>
                        <div className="text-lg font-bold text-[#FF9D00] font-mono mt-1">
                          {formatPct(selectedRun.answer_relevance_score)}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-[#0B0B0B] border border-[#262626]">
                        <div className="text-[11px] text-[#737373] font-mono">Avg Latency / Query</div>
                        <div className="text-lg font-bold text-[#F5F5F5] font-mono mt-1">
                          {formatMs(selectedRun.avg_latency_ms)}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Query Items & Ground Truth Comparison */}
                <Card>
                  <CardHeader>
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 w-full">
                      <CardTitle subtitle="Granular evaluation score per golden query">
                        <span>Query Test Matrix ({filteredItems.length})</span>
                      </CardTitle>

                      <div className="flex items-center gap-2">
                        <div className="relative">
                          <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-[#737373]" />
                          <input
                            type="text"
                            placeholder="Filter queries..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="bg-[#0B0B0B] border border-[#262626] rounded-lg pl-8 pr-3 py-1.5 text-xs text-[#F5F5F5] placeholder-[#737373] focus:outline-none focus:border-[#FF9D00]"
                          />
                        </div>

                        {categories.length > 0 && (
                          <select
                            value={categoryFilter}
                            onChange={(e) => setCategoryFilter(e.target.value)}
                            className="bg-[#0B0B0B] border border-[#262626] rounded-lg px-2.5 py-1.5 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#FF9D00]"
                          >
                            <option value="ALL">All Categories</option>
                            {categories.map((c) => (
                              <option key={c} value={c}>
                                {c}
                              </option>
                            ))}
                          </select>
                        )}
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="p-0">
                    <div className="divide-y divide-[#262626] max-h-[50vh] overflow-y-auto">
                      {filteredItems.map((item, idx) => (
                        <div
                          key={item.id || idx}
                          onClick={() => setInspectedItem(item)}
                          className="p-4 hover:bg-[#151515]/60 cursor-pointer transition-colors flex items-start justify-between gap-4"
                        >
                          <div className="space-y-1.5 flex-1 truncate">
                            <div className="flex items-center gap-2">
                              {item.category && (
                                <Badge variant="neutral">{item.category}</Badge>
                              )}
                              <span className="text-xs font-medium text-[#F5F5F5] truncate">
                                {item.query_text || (item as any).query}
                              </span>
                            </div>

                            <div className="text-[11px] text-[#737373] truncate">
                              <span>Expected: </span>
                              <span className="font-mono text-[#A1A1AA]">
                                {(item.expected_chunk_ids || (item as any).expected_chunks)?.length
                                  ? (item.expected_chunk_ids || (item as any).expected_chunks).join(', ')
                                  : 'None (Refusal test)'}
                              </span>
                            </div>
                          </div>

                          <div className="flex items-center gap-3 shrink-0 text-xs font-mono">
                            <div className="text-right">
                              <div className="text-[#737373]">R@5: <strong className="text-[#FF9D00]">{formatPct(item.recall_at_5)}</strong></div>
                              <div className="text-[10px] text-[#737373]">RR: {formatNum(item.reciprocal_rank, 2)}</div>
                            </div>
                            <ChevronRight className="w-4 h-4 text-[#737373]" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </div>
        </div>
      )}

      {/* RUN NEW EVALUATION MODAL */}
      {isRunModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-lg p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262626]">
              <h3 className="text-sm font-semibold font-display text-[#F5F5F5] flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-[#FF9D00]" />
                <span>Execute RAG Evaluation Benchmark</span>
              </h3>
              <button
                onClick={() => setIsRunModalOpen(false)}
                className="text-[#737373] hover:text-[#F5F5F5] p-1 rounded hover:bg-[#1A1A1A]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-900/60 text-rose-300 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleExecuteRun} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1.5">Target AI Employee</label>
                <select
                  value={selectedEmployeeId}
                  onChange={(e) => setSelectedEmployeeId(e.target.value)}
                  className="w-full bg-[#050505] border border-[#262626] rounded-lg px-3 py-2 text-[#F5F5F5] text-xs focus:outline-none focus:border-[#FF9D00]"
                >
                  {employees.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.name} ({e.role})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1.5">Benchmark Dataset</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setDatasetChoice('golden_hr')}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      datasetChoice === 'golden_hr'
                        ? 'bg-[#151515] border-[#FF9D00] text-[#F5F5F5] font-medium'
                        : 'bg-[#050505] border-[#262626] text-[#737373] hover:border-[#333333]'
                    }`}
                  >
                    <div className="text-xs">Golden HR Benchmark</div>
                    <div className="text-[10px] text-[#737373] mt-0.5">Authoritative 20-query test set</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => setDatasetChoice('custom')}
                    className={`p-3 rounded-lg border text-left transition-all ${
                      datasetChoice === 'custom'
                        ? 'bg-[#151515] border-[#FF9D00] text-[#F5F5F5] font-medium'
                        : 'bg-[#050505] border-[#262626] text-[#737373] hover:border-[#333333]'
                    }`}
                  >
                    <div className="text-xs">Custom JSONL</div>
                    <div className="text-[10px] text-[#737373] mt-0.5">Upload custom test cases</div>
                  </button>
                </div>
              </div>

              {datasetChoice === 'custom' && (
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1.5">JSONL Query Data</label>
                  <textarea
                    rows={4}
                    value={customJsonl}
                    onChange={(e) => setCustomJsonl(e.target.value)}
                    placeholder='{"query_id":"q1","query":"What is...","expected_chunks":["chunk1"]}'
                    className="w-full bg-[#050505] border border-[#262626] rounded-lg p-2 font-mono text-[11px] text-[#F5F5F5] focus:outline-none focus:border-[#FF9D00]"
                  />
                </div>
              )}

              <div className="flex items-center justify-between p-3 bg-[#0B0B0B] rounded-lg border border-[#262626]">
                <span className="text-[#A1A1AA] font-medium">Evaluate Generation Quality (Relevance & Refusals)</span>
                <input
                  type="checkbox"
                  checked={runGenEval}
                  onChange={(e) => setRunGenEval(e.target.checked)}
                  className="accent-[#FF9D00] cursor-pointer w-4 h-4"
                />
              </div>

              <div className="pt-3 border-t border-[#262626] flex items-center justify-between">
                <span className="text-[11px] text-[#FF9D00] font-mono">
                  {evalProgressMsg}
                </span>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={() => setIsRunModalOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="orange"
                    size="sm"
                    loading={runningEval}
                    icon={Play}
                  >
                    Launch
                  </Button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* REPORT MODAL */}
      {isReportModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-3xl p-6 shadow-2xl max-h-[85vh] flex flex-col space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262626] shrink-0">
              <h3 className="text-sm font-semibold font-display text-[#F5F5F5] flex items-center gap-2">
                <FileText className="w-4 h-4 text-[#FF9D00]" />
                <span>Executive Evaluation & Regression Report</span>
              </h3>
              <button
                onClick={() => setIsReportModalOpen(false)}
                className="text-[#737373] hover:text-[#F5F5F5] p-1 rounded hover:bg-[#1A1A1A]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 bg-[#050505] rounded-lg border border-[#262626] text-xs font-mono text-[#D4D4D8] whitespace-pre-wrap leading-relaxed">
              {reportLoading ? 'Generating executive evaluation report...' : reportMarkdown}
            </div>

            <div className="pt-3 flex justify-between items-center border-t border-[#262626] shrink-0">
              <Button
                variant="secondary"
                size="sm"
                icon={copiedReport ? Check : Copy}
                onClick={() => {
                  navigator.clipboard.writeText(reportMarkdown);
                  setCopiedReport(true);
                  setTimeout(() => setCopiedReport(false), 2000);
                }}
              >
                {copiedReport ? 'Copied' : 'Copy Report'}
              </Button>
              <Button
                variant="orange"
                size="sm"
                onClick={() => setIsReportModalOpen(false)}
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* ITEM INSPECTOR MODAL */}
      {inspectedItem && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-2xl p-6 shadow-2xl max-h-[85vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262626]">
              <h3 className="text-sm font-semibold font-display text-[#F5F5F5] flex items-center gap-2">
                <Search className="w-4 h-4 text-[#FF9D00]" />
                <span>Query Evaluation Inspection</span>
              </h3>
              <button
                onClick={() => setInspectedItem(null)}
                className="text-[#737373] hover:text-[#F5F5F5] p-1 rounded hover:bg-[#1A1A1A]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 text-xs text-[#A1A1AA]">
              <div className="p-3 bg-[#0B0B0B] rounded-lg border border-[#262626] space-y-1">
                <div className="text-[11px] text-[#737373] font-mono">Test Query:</div>
                <div className="text-[#F5F5F5] font-medium">{inspectedItem.query_text || (inspectedItem as any).query}</div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-[#0B0B0B] rounded-lg border border-[#262626]">
                  <div className="text-[11px] text-[#737373] font-mono">Category:</div>
                  <Badge variant="neutral">{inspectedItem.category || 'General'}</Badge>
                </div>
                <div className="p-3 bg-[#0B0B0B] rounded-lg border border-[#262626]">
                  <div className="text-[11px] text-[#737373] font-mono">Recall@5:</div>
                  <span className="font-mono text-[#FF9D00] font-bold">{formatPct(inspectedItem.recall_at_5)}</span>
                </div>
              </div>

              <div>
                <strong className="block text-[#737373] font-mono text-[11px] mb-1">Expected Golden Chunks:</strong>
                <pre className="p-2.5 bg-[#050505] rounded border border-[#262626] font-mono text-[11px] text-[#FF9D00]">
                  {JSON.stringify(inspectedItem.expected_chunk_ids || (inspectedItem as any).expected_chunks || [], null, 2)}
                </pre>
              </div>

              <div>
                <strong className="block text-[#737373] font-mono text-[11px] mb-1">Actual Retrieved Chunks:</strong>
                <pre className="p-2.5 bg-[#050505] rounded border border-[#262626] font-mono text-[11px] text-[#FFC247] max-h-40 overflow-y-auto">
                  {JSON.stringify(inspectedItem.retrieved_chunk_ids || (inspectedItem as any).retrieved_chunks || [], null, 2)}
                </pre>
              </div>

              {inspectedItem.generated_answer && (
                <div>
                  <strong className="block text-[#737373] font-mono text-[11px] mb-1">Generated Response:</strong>
                  <div className="p-3 bg-[#050505] rounded border border-[#262626] text-[#D4D4D8] text-xs whitespace-pre-wrap leading-relaxed">
                    {inspectedItem.generated_answer}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-[#262626] flex justify-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setInspectedItem(null)}
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
