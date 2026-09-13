'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { AIEmployee, AIEmployeeStatus } from '@/types';
import {
  Bot,
  Plus,
  Settings,
  Trash2,
  Edit2,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  X,
  Volume2,
  UserCheck,
  MessageSquare,
} from 'lucide-react';

export default function AIEmployeesPage() {
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<AIEmployee | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [description, setDescription] = useState('');
  const [personality, setPersonality] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [language, setLanguage] = useState('en');
  const [status, setStatus] = useState<AIEmployeeStatus>('DRAFT');

  const loadEmployees = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getAIEmployees();
      setEmployees(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch AI employees');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEmployees();
  }, []);

  const openCreateModal = () => {
    setEditingEmployee(null);
    setName('');
    setRole('');
    setDescription('');
    setPersonality('');
    setSystemPrompt('');
    setLanguage('en');
    setStatus('DRAFT');
    setIsModalOpen(true);
  };

  const openEditModal = (emp: AIEmployee) => {
    setEditingEmployee(emp);
    setName(emp.name);
    setRole(emp.role);
    setDescription(emp.description || '');
    setPersonality(emp.personality || '');
    setSystemPrompt(emp.system_prompt || '');
    setLanguage(emp.language || 'en');
    setStatus(emp.status);
    setIsModalOpen(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const payload = {
      name,
      role,
      description: description || undefined,
      personality: personality || undefined,
      system_prompt: systemPrompt || undefined,
      language,
      status,
    };

    try {
      if (editingEmployee) {
        await api.updateAIEmployee(editingEmployee.id, payload);
        setSuccess(`Updated AI Employee "${name}"`);
      } else {
        await api.createAIEmployee(payload);
        setSuccess(`Created AI Employee "${name}"`);
      }
      setIsModalOpen(false);
      loadEmployees();
    } catch (err: any) {
      setError(err.message || 'Failed to save AI employee');
    }
  };

  const handleDelete = async (id: string, empName: string) => {
    if (!confirm(`Are you sure you want to delete "${empName}"?`)) return;
    try {
      await api.deleteAIEmployee(id);
      setSuccess(`Deleted AI Employee "${empName}"`);
      loadEmployees();
    } catch (err: any) {
      setError(err.message || 'Failed to delete AI employee');
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">AI Employees</h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage your company&apos;s AI employees, define their roles, personalities, and system prompts.
          </p>
        </div>
        <button
          onClick={openCreateModal}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg shadow-sm transition-all"
        >
          <Plus className="w-4 h-4" />
          Create AI Employee
        </button>
      </div>

      {/* Notifications */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* List */}
      {loading ? (
        <div className="py-12 text-center text-sm text-slate-500">Loading AI employees...</div>
      ) : employees.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-slate-800 rounded-xl bg-slate-900/30">
          <Bot className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-200">No AI Employees Configured</h3>
          <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
            You haven&apos;t created any AI employees for this workspace yet. Click the button below to get started.
          </p>
          <button
            onClick={openCreateModal}
            className="mt-5 inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg"
          >
            <Plus className="w-4 h-4" /> Create AI Employee
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {employees.map((emp) => (
            <div
              key={emp.id}
              className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-slate-700 transition-all"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-bold">
                      <Bot className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-white text-base">{emp.name}</h3>
                      <p className="text-xs text-indigo-400 font-medium">{emp.role}</p>
                    </div>
                  </div>
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase font-semibold ${
                      emp.status === 'ACTIVE'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : emp.status === 'DRAFT'
                        ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                        : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                    }`}
                  >
                    {emp.status}
                  </span>
                </div>

                {emp.description && (
                  <p className="mt-3 text-xs text-slate-400 line-clamp-2">{emp.description}</p>
                )}

                {emp.personality && (
                  <div className="mt-3 p-2.5 rounded-lg bg-slate-800/40 border border-slate-800 text-xs">
                    <span className="font-medium text-slate-300">Personality: </span>
                    <span className="text-slate-400">{emp.personality}</span>
                  </div>
                )}

                {/* Future extension tags */}
                <div className="mt-4 flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    <UserCheck className="w-3 h-3 text-indigo-400" />
                    Lang: {emp.language}
                  </span>
                  <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    <Volume2 className="w-3 h-3 text-purple-400" />
                    Voice: Config Ready
                  </span>
                </div>
              </div>

              <div className="mt-5 pt-4 border-t border-slate-800 flex items-center justify-between gap-2">
                <Link
                  href={`/ai-employees/${emp.id}/chat`}
                  className="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-colors"
                >
                  <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Chat</span>
                </Link>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => openEditModal(emp)}
                    className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded transition-colors"
                    title="Edit Employee"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(emp.id, emp.name)}
                    className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded transition-colors"
                    title="Delete Employee"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create / Edit Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-indigo-400" />
                {editingEmployee ? 'Edit AI Employee' : 'Create New AI Employee'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSave} className="mt-4 space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Employee Name *
                  </label>
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Aura, Jarvis"
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Role / Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    placeholder="e.g. Senior Support Agent"
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Description
                </label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="High-level mandate and team function"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Personality & Tone
                </label>
                <input
                  type="text"
                  value={personality}
                  onChange={(e) => setPersonality(e.target.value)}
                  placeholder="e.g. Empathetic, analytical, concise"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  System Prompt (Core Directives)
                </label>
                <textarea
                  rows={4}
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="Core rules, behavioral guidelines, safety boundaries..."
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-xs"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Primary Language
                  </label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="en">English (en)</option>
                    <option value="es">Spanish (es)</option>
                    <option value="fr">French (fr)</option>
                    <option value="de">German (de)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Status</label>
                  <select
                    value={status}
                    onChange={(e) => setStatus(e.target.value as AIEmployeeStatus)}
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="DRAFT">Draft</option>
                    <option value="ACTIVE">Active</option>
                    <option value="INACTIVE">Inactive</option>
                  </select>
                </div>
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg shadow-sm"
                >
                  {editingEmployee ? 'Save Changes' : 'Create AI Employee'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
