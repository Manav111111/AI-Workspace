'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import {
  AIEmployee,
  BudgetStatus,
  UsageBudget,
  UsageLedgerEntry,
  UsageSummary,
} from '@/types';
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  Check,
  CheckCircle2,
  ChevronRight,
  Clock,
  Coins,
  Cpu,
  CreditCard,
  DollarSign,
  Filter,
  Layers,
  PieChart,
  Plus,
  RefreshCw,
  Search,
  ShieldAlert,
  ShieldCheck,
  Trash2,
  TrendingUp,
  X,
  Zap,
} from 'lucide-react';

export default function UsagePage() {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [ledger, setLedger] = useState<UsageLedgerEntry[]>([]);
  const [budgets, setBudgets] = useState<UsageBudget[]>([]);
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Filters
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('ALL');
  const [timeWindowDays, setTimeWindowDays] = useState<number>(30);

  // Create Budget Modal
  const [isBudgetModalOpen, setIsBudgetModalOpen] = useState(false);
  const [budgetName, setBudgetName] = useState('');
  const [budgetLimit, setBudgetLimit] = useState('50.00');
  const [budgetPeriod, setBudgetPeriod] = useState('MONTHLY');
  const [budgetSoftLimit, setBudgetSoftLimit] = useState(80);
  const [budgetHardLimit, setBudgetHardLimit] = useState(true);
  const [budgetEmployeeId, setBudgetEmployeeId] = useState('GLOBAL');
  const [creatingBudget, setCreatingBudget] = useState(false);
  const [budgetError, setBudgetError] = useState<string | null>(null);

  useEffect(() => {
    loadAll();
  }, []);

  async function loadAll() {
    setLoading(true);
    try {
      const [fetchedSummary, fetchedLedger, fetchedBudgets, fetchedEmployees] =
        await Promise.all([
          api.getUsageSummary(undefined, timeWindowDays),
          api.listUsageLedger(undefined, 50),
          api.listBudgets(),
          api.getAIEmployees(),
        ]);
      setSummary(fetchedSummary);
      setLedger(fetchedLedger);
      setBudgets(fetchedBudgets);
      setEmployees(fetchedEmployees);
    } catch (err) {
      console.error('Failed to load usage data:', err);
    } finally {
      setLoading(false);
    }
  }

  async function refreshData(empId?: string, days?: number) {
    setRefreshing(true);
    const activeEmp = (empId ?? selectedEmployeeId) !== 'ALL' ? (empId ?? selectedEmployeeId) : undefined;
    const activeDays = days ?? timeWindowDays;
    try {
      const [fetchedSummary, fetchedLedger, fetchedBudgets] = await Promise.all([
        api.getUsageSummary(activeEmp, activeDays),
        api.listUsageLedger(activeEmp, 50),
        api.listBudgets(),
      ]);
      setSummary(fetchedSummary);
      setLedger(fetchedLedger);
      setBudgets(fetchedBudgets);
    } catch (err) {
      console.error('Failed to refresh usage data:', err);
    } finally {
      setRefreshing(false);
    }
  }

  const handleCreateBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    setBudgetError(null);
    const limitNum = parseFloat(budgetLimit);
    if (isNaN(limitNum) || limitNum <= 0) {
      setBudgetError('Please enter a valid positive dollar limit');
      return;
    }
    if (!budgetName.trim()) {
      setBudgetError('Budget policy name is required');
      return;
    }

    setCreatingBudget(true);
    try {
      await api.createBudget({
        budget_name: budgetName.trim(),
        limit_amount: limitNum,
        period_type: budgetPeriod,
        soft_limit_percent: Number(budgetSoftLimit),
        hard_limit_enabled: budgetHardLimit,
        ai_employee_id: budgetEmployeeId !== 'GLOBAL' ? budgetEmployeeId : undefined,
      });
      setIsBudgetModalOpen(false);
      setBudgetName('');
      setBudgetLimit('50.00');
      await refreshData();
    } catch (err: any) {
      setBudgetError(err.message || 'Failed to create budget policy');
    } finally {
      setCreatingBudget(false);
    }
  };

  const handleDeleteBudget = async (id: string) => {
    if (!confirm('Are you sure you want to delete this budget governance policy?')) return;
    try {
      await api.deleteBudget(id);
      await refreshData();
    } catch (err) {
      console.error('Failed to delete budget policy', err);
    }
  };

  const getEmployeeName = (id?: string | null) => {
    if (!id) return 'Company-wide (All Employees)';
    const found = employees.find((e) => e.id === id);
    return found ? found.name : `${id.slice(0, 8)}...`;
  };

  const filteredLedger = useMemo(() => {
    if (selectedEmployeeId === 'ALL') return ledger;
    return ledger.filter((l) => l.ai_employee_id === selectedEmployeeId);
  }, [ledger, selectedEmployeeId]);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 space-y-6">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Coins className="w-6 h-6 text-emerald-400" />
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Cost Metering & Usage Governance
            </h1>
            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              Decimal-Safe Ledger
            </span>
          </div>
          <p className="text-sm text-slate-400">
            Real-time multi-tenant token consumption, exact pricing breakdown, and hard budget enforcement.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refreshData()}
            disabled={refreshing}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-slate-900 border border-slate-700/80 hover:bg-slate-800 text-slate-200 text-sm font-medium transition shadow-sm disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-emerald-400' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setIsBudgetModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition shadow-md shadow-emerald-950"
          >
            <Plus className="w-4 h-4" />
            New Spend Budget
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Cost */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">
              Estimated Spend ({timeWindowDays}d)
            </span>
            <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <DollarSign className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white mb-1 font-mono">
            ${summary?.total_estimated_cost.toFixed(4) ?? '0.0000'}
            <span className="text-xs text-slate-400 font-sans font-normal ml-1.5">USD</span>
          </div>
          <div className="text-xs text-slate-400 flex items-center gap-1">
            <span>Avg / Turn:</span>
            <span className="text-slate-200 font-mono font-medium">
              $
              {summary && summary.requests_count > 0
                ? (summary.total_estimated_cost / summary.requests_count).toFixed(5)
                : '0.00000'}
            </span>
          </div>
        </div>

        {/* Total Tokens */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Total Tokens</span>
            <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Zap className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white mb-1 font-mono">
            {summary?.total_tokens.toLocaleString() ?? '0'}
          </div>
          <div className="text-xs text-slate-400 flex items-center justify-between">
            <span>In: {summary?.input_tokens.toLocaleString() ?? 0}</span>
            <span className="text-slate-600">•</span>
            <span>Out: {summary?.output_tokens.toLocaleString() ?? 0}</span>
          </div>
        </div>

        {/* Total Turn Requests */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Turn Invocations</span>
            <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <BarChart3 className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white mb-1 font-mono">
            {summary?.requests_count.toLocaleString() ?? '0'}
          </div>
          <div className="text-xs text-slate-400">
            Across conversation, playground & eval turns
          </div>
        </div>

        {/* Active Budgets Count */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 backdrop-blur-sm shadow-md">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-slate-400">Governance Policies</span>
            <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-bold text-white mb-1">
            {budgets.length}
            <span className="text-xs text-slate-400 font-normal ml-1.5">active policies</span>
          </div>
          <div className="text-xs text-slate-400">
            {budgets.filter((b) => b.hard_limit_enabled).length} hard enforcement active
          </div>
        </div>
      </div>

      {/* Spend Budget Policies & Progress Section */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <CreditCard className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-white">Spend Budget Guardrails</h2>
          </div>
          <span className="text-xs text-slate-400">Pre-Invocation Balance Checks</span>
        </div>

        {summary?.budgets && summary.budgets.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {summary.budgets.map((b) => {
              const isExceeded = b.exceeded || b.utilization_percent >= 100;
              const isSoftWarn = b.utilization_percent >= b.soft_limit_percent;

              return (
                <div
                  key={b.id}
                  className={`p-4 rounded-xl border transition shadow-sm ${
                    isExceeded
                      ? 'bg-rose-950/20 border-rose-800/60'
                      : isSoftWarn
                      ? 'bg-amber-950/20 border-amber-800/60'
                      : 'bg-slate-950/60 border-slate-800'
                  }`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="text-sm font-bold text-white">{b.name}</h3>
                      <p className="text-[11px] text-slate-400">
                        {getEmployeeName(b.ai_employee_id)} • {b.period}
                      </p>
                    </div>
                    <button
                      onClick={() => handleDeleteBudget(b.id)}
                      className="p-1 text-slate-500 hover:text-rose-400 transition"
                      title="Delete Policy"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>

                  {/* Spend vs Limit */}
                  <div className="flex items-baseline justify-between mt-3 mb-1 text-xs">
                    <span className="text-slate-400">
                      Spent: <strong className="font-mono text-white">${b.current_spend.toFixed(4)}</strong>
                    </span>
                    <span className="text-slate-400">
                      Limit: <strong className="font-mono text-slate-200">${b.limit_amount.toFixed(2)}</strong>
                    </span>
                  </div>

                  {/* Visual Progress Bar */}
                  <div className="relative w-full h-2.5 bg-slate-900 rounded-full overflow-hidden mb-2">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        isExceeded
                          ? 'bg-rose-500'
                          : isSoftWarn
                          ? 'bg-amber-500'
                          : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, b.utilization_percent)}%` }}
                    />
                    {/* Soft limit marker line */}
                    <div
                      className="absolute top-0 bottom-0 w-0.5 bg-white/40"
                      style={{ left: `${b.soft_limit_percent}%` }}
                      title={`Soft warning threshold at ${b.soft_limit_percent}%`}
                    />
                  </div>

                  {/* Status Badges */}
                  <div className="flex items-center justify-between text-[11px]">
                    <span
                      className={`font-semibold ${
                        isExceeded
                          ? 'text-rose-400'
                          : isSoftWarn
                          ? 'text-amber-400'
                          : 'text-emerald-400'
                      }`}
                    >
                      {b.utilization_percent}% utilized
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        b.hard_limit_enabled
                          ? 'bg-rose-500/10 text-rose-300 border border-rose-500/20'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {b.hard_limit_enabled ? 'Hard Enforcement' : 'Soft Alert Only'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="p-6 text-center text-slate-400 border border-dashed border-slate-800 rounded-lg">
            <ShieldAlert className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-300 font-medium">No Spend Budgets Configured</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Protect against rogue agent loops or unexpected token surges by creating a budget policy.
            </p>
          </div>
        )}
      </div>

      {/* Model & Source Breakdown Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Model Breakdown */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-slate-200">
            <Cpu className="w-4 h-4 text-purple-400" />
            <span>Spend by LLM Model</span>
          </div>
          {summary?.by_model && summary.by_model.length > 0 ? (
            <div className="space-y-2">
              {summary.by_model.map((m) => (
                <div
                  key={m.model}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs"
                >
                  <div>
                    <span className="font-mono text-purple-400 font-medium">{m.model}</span>
                    <span className="text-[11px] text-slate-500 block">
                      {m.tokens.toLocaleString()} tokens
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="font-mono font-semibold text-white">
                      ${m.estimated_cost.toFixed(4)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 text-center text-slate-500 text-xs">No model usage recorded.</div>
          )}
        </div>

        {/* Source Breakdown */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <div className="flex items-center gap-2 mb-3 text-xs font-semibold text-slate-200">
            <Layers className="w-4 h-4 text-cyan-400" />
            <span>Usage by Execution Source</span>
          </div>
          {summary?.by_source && summary.by_source.length > 0 ? (
            <div className="space-y-2">
              {summary.by_source.map((s) => (
                <div
                  key={s.source}
                  className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs"
                >
                  <div>
                    <span className="font-mono text-cyan-400 font-medium">{s.source}</span>
                    <span className="text-[11px] text-slate-500 block">
                      {s.requests} invocations
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="font-mono font-semibold text-slate-300">
                      {s.tokens.toLocaleString()} tokens
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4 text-center text-slate-500 text-xs">No source usage recorded.</div>
          )}
        </div>
      </div>

      {/* Filter and Ledger Table Section */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-lg space-y-0">
        <div className="px-5 py-4 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Coins className="w-4 h-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-white">Authoritative Usage Ledger</h2>
            <span className="text-xs text-slate-500">({filteredLedger.length} entries)</span>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={selectedEmployeeId}
              onChange={(e) => {
                setSelectedEmployeeId(e.target.value);
                refreshData(e.target.value);
              }}
              className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-emerald-500"
            >
              <option value="ALL">All AI Employees</option>
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading ? (
          <div className="py-16 text-center text-slate-400 flex flex-col items-center justify-center gap-2">
            <RefreshCw className="w-6 h-6 animate-spin text-emerald-400" />
            <p className="text-sm">Loading usage ledger records...</p>
          </div>
        ) : filteredLedger.length === 0 ? (
          <div className="py-16 text-center text-slate-400">
            <Coins className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <p className="text-sm font-medium text-slate-300">No ledger entries recorded</p>
            <p className="text-xs text-slate-500 mt-1">
              Token usage ledger entries are recorded synchronously for every model invocation.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950/50 text-slate-400 font-medium">
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">AI Employee</th>
                  <th className="py-3 px-4">Model & Provider</th>
                  <th className="py-3 px-4">Operation</th>
                  <th className="py-3 px-4">Tokens (In / Out / Tot)</th>
                  <th className="py-3 px-4 text-right">Cost (USD)</th>
                  <th className="py-3 px-4 text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {filteredLedger.map((row) => (
                  <tr key={row.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-4 text-slate-400">
                      {new Date(row.created_at).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                        second: '2-digit',
                      })}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-300">
                      {getEmployeeName(row.ai_employee_id)}
                    </td>
                    <td className="py-3 px-4 font-mono text-purple-400">
                      <span>{row.model}</span>
                      <span className="text-[10px] text-slate-500 block">{row.provider}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded font-mono text-[11px] bg-slate-800 text-slate-300 border border-slate-700">
                        {row.operation_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">
                      <span>
                        {row.input_tokens.toLocaleString()} / {row.output_tokens.toLocaleString()}
                      </span>
                      <span className="text-slate-500 text-[11px] block">
                        tot: {row.total_tokens.toLocaleString()}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-mono font-medium text-emerald-400">
                      ${row.estimated_cost.toFixed(6)}
                    </td>
                    <td className="py-3 px-4 text-center">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {row.cost_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Create Budget Modal */}
      {isBudgetModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-emerald-400" />
                <h3 className="text-base font-bold text-white">Create Spend Budget Policy</h3>
              </div>
              <button
                onClick={() => setIsBudgetModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {budgetError && (
              <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300 flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{budgetError}</span>
              </div>
            )}

            <form onSubmit={handleCreateBudget} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Budget Policy Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Monthly Global Token Cap"
                  value={budgetName}
                  onChange={(e) => setBudgetName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Limit Amount (USD) *
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-2.5 text-slate-500">$</span>
                    <input
                      type="number"
                      step="0.01"
                      required
                      min="0.01"
                      value={budgetLimit}
                      onChange={(e) => setBudgetLimit(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg py-2.5 pl-7 pr-3 text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">
                    Period Frequency
                  </label>
                  <select
                    value={budgetPeriod}
                    onChange={(e) => setBudgetPeriod(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    <option value="MONTHLY">Monthly</option>
                    <option value="WEEKLY">Weekly</option>
                    <option value="DAILY">Daily</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">
                  Scope Target
                </label>
                <select
                  value={budgetEmployeeId}
                  onChange={(e) => setBudgetEmployeeId(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  <option value="GLOBAL">Company-wide (All AI Employees)</option>
                  {employees.map((emp) => (
                    <option key={emp.id} value={emp.id}>
                      {emp.name} (Specific Employee)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-slate-300 font-medium">
                    Soft Limit Warning Threshold
                  </label>
                  <span className="font-mono text-emerald-400 font-semibold">
                    {budgetSoftLimit}%
                  </span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="99"
                  value={budgetSoftLimit}
                  onChange={(e) => setBudgetSoftLimit(Number(e.target.value))}
                  className="w-full accent-emerald-500 cursor-pointer"
                />
                <p className="text-[11px] text-slate-500 mt-1">
                  Alerts are issued when usage reaches {budgetSoftLimit}% of the configured limit.
                </p>
              </div>

              <div className="pt-2 border-t border-slate-800">
                <label className="flex items-start gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={budgetHardLimit}
                    onChange={(e) => setBudgetHardLimit(e.target.checked)}
                    className="mt-0.5 rounded border-slate-800 bg-slate-950 accent-emerald-500"
                  />
                  <div>
                    <span className="font-semibold text-slate-200">
                      Enforce Hard Limit Block
                    </span>
                    <p className="text-[11px] text-slate-400">
                      When enabled, any LLM invocation exceeding 100% of this budget will return an HTTP 429 BUDGET_EXCEEDED error.
                    </p>
                  </div>
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsBudgetModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingBudget}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition shadow-md shadow-emerald-950 disabled:opacity-50"
                >
                  {creatingBudget ? 'Creating...' : 'Save Budget Policy'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
