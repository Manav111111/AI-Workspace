'use client';

import React, { useEffect, useState, useMemo } from 'react';
import { api } from '@/lib/api';
import {
  AIEmployee,
  UsageBudget,
  UsageLedgerEntry,
  UsageSummary,
} from '@/types';
import {
  BarChart3,
  DollarSign,
  Plus,
  RefreshCw,
  ShieldCheck,
  Trash2,
  X,
  Zap,
} from 'lucide-react';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';

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
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Top Header */}
      <PageHeader
        title="Cost Metering & Budget Governance"
        description="Real-time multi-tenant token consumption, exact pricing breakdown from model registry, and hard budget governance enforcement."
        badge={<Badge variant="orange">Decimal-Safe Ledger</Badge>}
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              icon={RefreshCw}
              loading={refreshing}
              onClick={() => refreshData()}
            >
              Refresh
            </Button>
            <Button
              variant="orange"
              size="sm"
              icon={Plus}
              onClick={() => setIsBudgetModalOpen(true)}
            >
              New Spend Budget
            </Button>
          </div>
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Cost */}
        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-[#737373]">
                Estimated Spend ({timeWindowDays}d)
              </span>
              <div className="p-1.5 rounded-lg bg-[#151515] border border-[#262626] text-[#FF9D00]">
                <DollarSign className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-[#F5F5F5] font-mono mb-1">
              ${summary?.total_estimated_cost.toFixed(4) ?? '0.0000'}
              <span className="text-xs text-[#737373] font-normal ml-1.5 font-sans">USD</span>
            </div>
            <div className="text-xs text-[#737373] flex items-center gap-1 font-mono">
              <span>Avg/Turn:</span>
              <span className="text-[#A1A1AA] font-semibold">
                $
                {summary && summary.requests_count > 0
                  ? (summary.total_estimated_cost / summary.requests_count).toFixed(5)
                  : '0.00000'}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Total Tokens */}
        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-[#737373]">Total Tokens</span>
              <div className="p-1.5 rounded-lg bg-[#151515] border border-[#262626] text-[#A1A1AA]">
                <Zap className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-[#F5F5F5] font-mono mb-1">
              {summary?.total_tokens.toLocaleString() ?? '0'}
            </div>
            <div className="text-xs text-[#737373] font-mono">
              In: {summary?.input_tokens.toLocaleString() ?? '0'} &bull; Out: {summary?.output_tokens.toLocaleString() ?? '0'}
            </div>
          </CardContent>
        </Card>

        {/* Total Invocations */}
        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-[#737373]">Metered Calls</span>
              <div className="p-1.5 rounded-lg bg-[#151515] border border-[#262626] text-[#FFC247]">
                <BarChart3 className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-[#F5F5F5] font-mono mb-1">
              {summary?.requests_count ?? 0}
            </div>
            <div className="text-xs text-emerald-400 font-medium">
              100% Accounted in Ledger
            </div>
          </CardContent>
        </Card>

        {/* Budget Policies Active */}
        <Card hover>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-[#737373]">Budget Policies</span>
              <div className="p-1.5 rounded-lg bg-[#151515] border border-[#262626] text-amber-400">
                <ShieldCheck className="w-4 h-4" />
              </div>
            </div>
            <div className="text-2xl font-bold text-[#FFC247] font-mono mb-1">
              {budgets.length}
            </div>
            <div className="text-xs text-[#737373]">
              {budgets.filter((b) => b.hard_limit_enabled).length} hard limit policies active
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Model Breakdown & Active Budgets Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Model Breakdown Card */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle subtitle="Model price registry token spend distribution">
              <span>Spend by Model</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {!summary?.by_model || (Array.isArray(summary.by_model) && summary.by_model.length === 0) ? (
              <div className="text-center py-6 text-xs text-[#737373] font-mono">
                No model usage recorded yet.
              </div>
            ) : (
              (Array.isArray(summary.by_model)
                ? summary.by_model
                : Object.entries(summary.by_model).map(([model, data]: [string, any]) => ({ model, ...data }))
              ).map((mData: any) => {
                const modelName = mData.model;
                const cost = mData.cost ?? mData.estimated_cost ?? 0;
                const tokens = mData.tokens ?? 0;
                const pct = summary.total_estimated_cost > 0
                  ? (cost / summary.total_estimated_cost) * 100
                  : 0;
                return (
                  <div key={modelName} className="space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[#F5F5F5] font-medium">{modelName}</span>
                      <span className="font-mono text-[#FF9D00] font-bold">${Number(cost).toFixed(4)}</span>
                    </div>
                    <div className="w-full bg-[#151515] h-1.5 rounded-full overflow-hidden">
                      <div
                        className="bg-[#FF9D00] h-full rounded-full"
                        style={{ width: `${Math.max(6, pct)}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-[#737373] font-mono">
                      <span>{Number(tokens).toLocaleString()} tokens</span>
                      <span>{pct.toFixed(1)}% of total</span>
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        {/* Spend Budget Policies List */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle subtitle="Real-time spend caps with soft alerts and hard request rejection">
              <span>Active Budget Governance Policies ({budgets.length})</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {budgets.length === 0 ? (
              <div className="text-center py-8 text-xs text-[#737373] border border-dashed border-[#262626] rounded-lg">
                No budget policies created. Set spend limits to protect against unexpected token spikes.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                {budgets.map((b: any) => {
                  const currentSpend = b.current_spend ?? 0;
                  const percentUsed = b.limit_amount > 0 ? (currentSpend / b.limit_amount) * 100 : 0;
                  const isWarning = percentUsed >= (b.soft_limit_percent || 80);
                  const isExceeded = percentUsed >= 100;

                  return (
                    <div
                      key={b.id}
                      className="p-3.5 rounded-lg bg-[#0B0B0B] border border-[#262626] space-y-2.5 flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-start justify-between">
                          <div>
                            <h4 className="text-xs font-semibold text-[#F5F5F5]">{b.budget_name}</h4>
                            <p className="text-[11px] text-[#737373] font-mono mt-0.5">
                              {getEmployeeName(b.ai_employee_id)}
                            </p>
                          </div>
                          <Badge
                            variant={isExceeded ? 'rose' : isWarning ? 'amber' : 'forest'}
                            dot
                          >
                            {isExceeded ? 'EXCEEDED' : isWarning ? 'WARNING' : 'HEALTHY'}
                          </Badge>
                        </div>

                        <div className="mt-3 text-sm font-bold font-mono text-[#F5F5F5]">
                          ${Number(currentSpend).toFixed(2)}{' '}
                          <span className="text-xs text-[#737373] font-normal">/ ${Number(b.limit_amount).toFixed(2)}</span>
                        </div>

                        <div className="w-full bg-[#151515] h-1.5 rounded-full overflow-hidden mt-1.5">
                          <div
                            className={`h-full rounded-full ${
                              isExceeded ? 'bg-rose-500' : isWarning ? 'bg-amber-500' : 'bg-[#FF9D00]'
                            }`}
                            style={{ width: `${Math.min(100, percentUsed)}%` }}
                          />
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-2 border-t border-[#262626] text-[10px] text-[#737373] font-mono">
                        <span>Period: {b.period_type}</span>
                        <button
                          onClick={() => handleDeleteBudget(b.id)}
                          className="text-[#737373] hover:text-rose-400 transition-colors p-1"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Usage Ledger Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <CardTitle subtitle="Immutable, decimal-safe per-request transaction accounting">
              <span>Usage Transaction Ledger</span>
            </CardTitle>

            <select
              value={selectedEmployeeId}
              onChange={(e) => setSelectedEmployeeId(e.target.value)}
              className="bg-[#0B0B0B] border border-[#262626] rounded-lg px-3 py-1.5 text-xs text-[#F5F5F5] focus:outline-none focus:border-[#FF9D00]"
            >
              <option value="ALL">All AI Employees</option>
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name}
                </option>
              ))}
            </select>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#262626] bg-[#0B0B0B] text-[11px] font-mono text-[#737373] uppercase tracking-wider">
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">AI Employee</th>
                  <th className="py-3 px-4">Model</th>
                  <th className="py-3 px-4">In Tokens</th>
                  <th className="py-3 px-4">Out Tokens</th>
                  <th className="py-3 px-4">Total Tokens</th>
                  <th className="py-3 px-4 text-right">Calculated Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#262626] font-mono text-[11px]">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-[#737373] font-sans">
                      Loading ledger entries...
                    </td>
                  </tr>
                ) : filteredLedger.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-10 text-center text-[#737373] font-sans">
                      No usage entries recorded for this selection.
                    </td>
                  </tr>
                ) : (
                  filteredLedger.map((row) => (
                    <tr key={row.id} className="hover:bg-[#151515]/60 transition-colors">
                      <td className="py-3 px-4 text-[#737373]">
                        {new Date(row.created_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })}
                      </td>
                      <td className="py-3 px-4 font-sans text-[#F5F5F5] font-medium">
                        {getEmployeeName(row.ai_employee_id)}
                      </td>
                      <td className="py-3 px-4 text-[#FF9D00]">{row.model}</td>
                      <td className="py-3 px-4 text-[#737373]">{(row.input_tokens || 0).toLocaleString()}</td>
                      <td className="py-3 px-4 text-[#737373]">{(row.output_tokens || 0).toLocaleString()}</td>
                      <td className="py-3 px-4 font-bold text-[#F5F5F5]">
                        {(row.total_tokens || 0).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right font-bold text-[#FF9D00]">
                        ${(row.estimated_cost || 0).toFixed(5)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* CREATE BUDGET MODAL */}
      {isBudgetModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262626]">
              <h3 className="text-sm font-semibold font-display text-[#F5F5F5] flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-[#FF9D00]" />
                <span>Create Spend Budget Policy</span>
              </h3>
              <button
                onClick={() => setIsBudgetModalOpen(false)}
                className="text-[#737373] hover:text-[#F5F5F5] p-1 rounded hover:bg-[#1A1A1A]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {budgetError && (
              <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-900/60 text-rose-300 text-xs">
                {budgetError}
              </div>
            )}

            <form onSubmit={handleCreateBudget} className="space-y-4 text-xs">
              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1.5">Policy Name *</label>
                <input
                  type="text"
                  required
                  value={budgetName}
                  onChange={(e) => setBudgetName(e.target.value)}
                  placeholder="e.g. Monthly Support Budget"
                  className="w-full bg-[#050505] border border-[#262626] rounded-lg px-3.5 py-2 text-[#F5F5F5] placeholder-[#737373] focus:outline-none focus:border-[#FF9D00]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1.5">Spend Cap ($ USD) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="1"
                    required
                    value={budgetLimit}
                    onChange={(e) => setBudgetLimit(e.target.value)}
                    className="w-full bg-[#050505] border border-[#262626] rounded-lg px-3.5 py-2 text-[#F5F5F5] font-mono focus:outline-none focus:border-[#FF9D00]"
                  />
                </div>

                <div>
                  <label className="block text-[#A1A1AA] font-medium mb-1.5">Reset Interval</label>
                  <select
                    value={budgetPeriod}
                    onChange={(e) => setBudgetPeriod(e.target.value)}
                    className="w-full bg-[#050505] border border-[#262626] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#FF9D00]"
                  >
                    <option value="MONTHLY">Monthly</option>
                    <option value="DAILY">Daily</option>
                    <option value="LIFETIME">Lifetime Cap</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[#A1A1AA] font-medium mb-1.5">Target AI Employee</label>
                <select
                  value={budgetEmployeeId}
                  onChange={(e) => setBudgetEmployeeId(e.target.value)}
                  className="w-full bg-[#050505] border border-[#262626] rounded-lg px-3 py-2 text-[#F5F5F5] focus:outline-none focus:border-[#FF9D00]"
                >
                  <option value="GLOBAL">Company-wide (All Employees)</option>
                  {employees.map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="p-3 bg-[#0B0B0B] rounded-lg border border-[#262626] flex items-center justify-between">
                <div>
                  <div className="text-[#F5F5F5] font-medium">Hard Enforcement</div>
                  <div className="text-[10px] text-[#737373]">Block model requests once cap is reached</div>
                </div>
                <input
                  type="checkbox"
                  checked={budgetHardLimit}
                  onChange={(e) => setBudgetHardLimit(e.target.checked)}
                  className="w-4 h-4 accent-[#FF9D00] cursor-pointer"
                />
              </div>

              <div className="pt-3 border-t border-[#262626] flex justify-end gap-2">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsBudgetModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="orange"
                  size="sm"
                  loading={creatingBudget}
                >
                  Create Policy
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
