'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { AIEmployee } from '@/types';
import { Bot, Plus, BookOpen, MessageSquare, ShieldCheck, ArrowUpRight, Activity } from 'lucide-react';

export default function DashboardPage() {
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getAIEmployees();
        setEmployees(data);
      } catch (err) {
        // Handled in UI
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      {/* Page Title & Quick Action */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Workspace Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Overview of your company&apos;s AI employees and platform foundation.
          </p>
        </div>
        <Link
          href="/ai-employees"
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg shadow-sm transition-all"
        >
          <Plus className="w-4 h-4" />
          Manage AI Employees
        </Link>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total AI Employees</span>
            <Bot className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">
            {loading ? '-' : employees.length}
          </div>
          <div className="mt-2 text-xs text-slate-400 flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span>
              {employees.filter((e) => e.status === 'ACTIVE').length} Active status
            </span>
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Knowledge Base</span>
            <BookOpen className="w-4 h-4 text-purple-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-white">Phase 1</div>
          <div className="mt-2 text-xs text-slate-400">
            RAG ingestion pipeline blueprint ready
          </div>
        </div>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Tenant Boundary</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="mt-3 text-3xl font-bold text-emerald-400">Isolated</div>
          <div className="mt-2 text-xs text-slate-400">
            Database queries strictly scoped by company_id
          </div>
        </div>
      </div>

      {/* Current AI Employees Section */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-100">AI Employees</h2>
          <Link
            href="/ai-employees"
            className="text-xs font-medium text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
          >
            View all <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {loading ? (
          <div className="py-8 text-center text-sm text-slate-500">Loading AI employees...</div>
        ) : employees.length === 0 ? (
          <div className="py-10 text-center border border-dashed border-slate-800 rounded-lg">
            <Bot className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <h3 className="text-sm font-medium text-slate-300">No AI employees created yet</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
              Create your first AI employee for this workspace to begin configuring its role, personality, and system prompt.
            </p>
            <Link
              href="/ai-employees"
              className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium rounded-lg"
            >
              <Plus className="w-3.5 h-3.5" /> Create AI Employee
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {employees.map((emp) => (
              <div
                key={emp.id}
                className="p-4 rounded-lg bg-slate-800/40 border border-slate-700/60 hover:border-slate-600 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-white">{emp.name}</h3>
                    <p className="text-xs text-indigo-400">{emp.role}</p>
                  </div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase font-semibold ${
                      emp.status === 'ACTIVE'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}
                  >
                    {emp.status}
                  </span>
                </div>
                {emp.description && (
                  <p className="mt-2 text-xs text-slate-400 line-clamp-2">{emp.description}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
