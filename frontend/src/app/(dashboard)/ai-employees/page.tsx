'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { AIEmployee, AIEmployeeStatus, KnowledgeBase, ToolDefinition } from '@/types';
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
  BookOpen,
  ShieldAlert,
  Layers,
  CheckSquare,
  Square,
  Wrench,
  ShieldCheck,
  FileCheck,
} from 'lucide-react';

export default function AIEmployeesPage() {
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [allKnowledgeBases, setAllKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [allTools, setAllTools] = useState<ToolDefinition[]>([]);
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
  const [selectedKbIds, setSelectedKbIds] = useState<string[]>([]);
  const [selectedToolNames, setSelectedToolNames] = useState<string[]>([]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [empData, kbData, toolData] = await Promise.all([
        api.getAIEmployees(),
        api.getKnowledgeBases().catch(() => []),
        api.getTools().catch(() => []),
      ]);
      setEmployees(empData);
      setAllKnowledgeBases(kbData);
      setAllTools(toolData);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
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
    setSelectedKbIds([]);
    setSelectedToolNames(['product_search', 'order_lookup']); // Default safe READ tools
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
    const assignedIds =
      emp.knowledge_base_ids ||
      (emp.assigned_knowledge_bases ? emp.assigned_knowledge_bases.map((k) => k.id) : []);
    setSelectedKbIds(assignedIds);
    const assignedToolList =
      emp.tool_names ||
      (emp.assigned_tools ? emp.assigned_tools.map((t) => t.tool_name) : []);
    setSelectedToolNames(assignedToolList);
    setIsModalOpen(true);
  };

  const toggleKbSelection = (kbId: string) => {
    setSelectedKbIds((prev) =>
      prev.includes(kbId) ? prev.filter((id) => id !== kbId) : [...prev, kbId]
    );
  };

  const toggleToolSelection = (toolName: string) => {
    setSelectedToolNames((prev) =>
      prev.includes(toolName) ? prev.filter((n) => n !== toolName) : [...prev, toolName]
    );
  };

  const selectAllKbs = () => {
    setSelectedKbIds(allKnowledgeBases.map((k) => k.id));
  };

  const clearAllKbs = () => {
    setSelectedKbIds([]);
  };

  const selectAllTools = () => {
    setSelectedToolNames(allTools.map((t) => t.name));
  };

  const clearAllTools = () => {
    setSelectedToolNames([]);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);

    const payload: any = {
      name,
      role,
      description: description || undefined,
      personality: personality || undefined,
      system_prompt: systemPrompt || undefined,
      language,
      status,
      knowledge_base_ids: selectedKbIds,
      tools: selectedToolNames,
    };

    try {
      if (editingEmployee) {
        await api.updateAIEmployee(editingEmployee.id, payload);
        setSuccess(`Updated AI Employee "${name}" with ${selectedKbIds.length} KBs and ${selectedToolNames.length} tools.`);
      } else {
        await api.createAIEmployee(payload);
        setSuccess(`Created AI Employee "${name}" with ${selectedKbIds.length} KBs and ${selectedToolNames.length} tools.`);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to save AI employee');
    }
  };

  const handleDelete = async (id: string, empName: string) => {
    if (!confirm(`Are you sure you want to delete AI Employee "${empName}"?`)) return;

    try {
      await api.deleteAIEmployee(id);
      setSuccess(`Deleted AI Employee "${empName}"`);
      loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to delete AI employee');
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-100">AI Employees</h1>
            <span className="px-2 py-0.5 text-xs rounded bg-indigo-500/20 text-indigo-400 font-medium border border-indigo-500/30">
              Role & Knowledge Scoped
            </span>
          </div>
          <p className="mt-1 text-sm text-slate-400">
            Configure AI personas, behavioral instructions, and assign specific knowledge bases for scoped RAG retrieval.
          </p>
        </div>

        <button
          onClick={openCreateModal}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors shadow-lg shadow-indigo-500/20 self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>Create AI Employee</span>
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-center gap-3 text-rose-400 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center gap-3 text-emerald-400 text-sm">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Grid of Employees */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-64 rounded-xl bg-slate-900/40 border border-slate-800 animate-pulse"
            />
          ))}
        </div>
      ) : employees.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-slate-800 rounded-xl bg-slate-900/20">
          <div className="w-12 h-12 rounded-xl bg-indigo-600/10 text-indigo-400 flex items-center justify-center mx-auto mb-4">
            <Bot className="w-6 h-6" />
          </div>
          <h3 className="text-base font-medium text-slate-200">No AI employees yet</h3>
          <p className="mt-1 text-sm text-slate-400 max-w-sm mx-auto">
            Create your first AI employee and grant it access to specific company knowledge bases.
          </p>
          <button
            onClick={openCreateModal}
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Create AI Employee</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {employees.map((emp) => (
            <div
              key={emp.id}
              className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 hover:border-slate-700 transition-colors flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
                      <Bot className="w-5 h-5" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-200 text-sm">{emp.name}</h3>
                      <p className="text-xs text-indigo-400 font-medium">{emp.role}</p>
                    </div>
                  </div>

                  <span
                    className={`text-[10px] px-2 py-0.5 rounded font-semibold tracking-wider ${
                      emp.status === 'ACTIVE'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-slate-800 text-slate-400'
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

                {/* Scoped Knowledge Access Badge Section */}
                <div className="mt-3.5 pt-3 border-t border-slate-800/80">
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="text-slate-300 font-medium flex items-center gap-1.5">
                      <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                      Knowledge Access:
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono">
                      {emp.assigned_knowledge_bases?.length || 0} assigned
                    </span>
                  </div>

                  {emp.assigned_knowledge_bases && emp.assigned_knowledge_bases.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5 mt-1.5">
                      {emp.assigned_knowledge_bases.map((kb) => (
                        <span
                          key={kb.id}
                          className="px-2 py-0.5 rounded-md bg-indigo-950/70 border border-indigo-800/60 text-indigo-300 text-[11px] font-medium flex items-center gap-1"
                        >
                          <Layers className="w-2.5 h-2.5 text-indigo-400" />
                          {kb.name}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-[11px] text-amber-400/80 bg-amber-950/20 border border-amber-900/40 px-2 py-1 rounded flex items-center gap-1.5 mt-1">
                      <ShieldAlert className="w-3 h-3 text-amber-400 shrink-0" />
                      <span>No knowledge bases assigned (Pure Persona)</span>
                    </div>
                  )}
                </div>

                {/* Assigned Tool Capabilities Badge Section */}
                <div className="mt-2.5 pt-2.5 border-t border-slate-800/60">
                  <div className="flex items-center justify-between text-xs mb-1.5">
                    <span className="text-slate-300 font-medium flex items-center gap-1.5">
                      <Wrench className="w-3.5 h-3.5 text-emerald-400" />
                      Assigned Tools:
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono">
                      {emp.tools?.length || emp.assigned_tools?.length || 0} active
                    </span>
                  </div>

                  {(emp.tools && emp.tools.length > 0) || (emp.assigned_tools && emp.assigned_tools.length > 0) ? (
                    <div className="flex flex-wrap gap-1.5 mt-1">
                      {(emp.tools || emp.assigned_tools?.map((t) => t.tool_name) || []).map((toolName) => (
                        <span
                          key={toolName}
                          className="px-2 py-0.5 rounded-md bg-emerald-950/60 border border-emerald-800/50 text-emerald-300 text-[10px] font-mono flex items-center gap-1"
                        >
                          <ShieldCheck className="w-2.5 h-2.5 text-emerald-400" />
                          {toolName}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="text-[11px] text-slate-400 bg-slate-800/40 border border-slate-700/40 px-2 py-0.5 rounded flex items-center gap-1.5 mt-1">
                      <span>No tools assigned (Read-only chat)</span>
                    </div>
                  )}
                </div>

                {/* Platform Capabilities */}
                <div className="mt-3 flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    <UserCheck className="w-3 h-3 text-indigo-400" />
                    Lang: {emp.language}
                  </span>
                  <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                    <Volume2 className="w-3 h-3 text-purple-400" />
                    Voice Ready
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
                    title="Edit Employee & Knowledge Access"
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

      {/* Create / Edit Modal with Knowledge Access Checklist */}
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
                    placeholder="e.g. Alex, Maya"
                    className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Role / Job Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    placeholder="e.g. AI Engineer, HR Specialist"
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
                  placeholder="Mandate and primary function within the company"
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
                  placeholder="e.g. Friendly, technical, concise, empathetic"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  System Instructions (Prompt Directives)
                </label>
                <textarea
                  rows={3}
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  placeholder="Define role behavioral boundaries and instructions..."
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-xs"
                />
              </div>

              {/* KNOWLEDGE ACCESS CHECKLIST */}
              <div className="p-3.5 rounded-lg bg-slate-800/50 border border-slate-700/80 space-y-2.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                    <BookOpen className="w-4 h-4 text-indigo-400" />
                    Knowledge Access (Scoped Retrieval)
                  </label>
                  {allKnowledgeBases.length > 0 && (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={selectAllKbs}
                        className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium"
                      >
                        Select All
                      </button>
                      <span className="text-slate-600">•</span>
                      <button
                        type="button"
                        onClick={clearAllKbs}
                        className="text-[11px] text-slate-400 hover:text-slate-300"
                      >
                        Clear
                      </button>
                    </div>
                  )}
                </div>

                <p className="text-[11px] text-slate-400">
                  Select which knowledge bases this AI Employee can retrieve from. Unselected knowledge will never be accessed or leaked.
                </p>

                {allKnowledgeBases.length === 0 ? (
                  <div className="text-center py-4 bg-slate-900/60 rounded-lg border border-dashed border-slate-800 text-xs text-slate-400">
                    No knowledge bases found in your company.{' '}
                    <Link href="/knowledge" className="text-indigo-400 hover:underline">
                      Create a Knowledge Base
                    </Link>{' '}
                    first.
                  </div>
                ) : (
                  <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                    {allKnowledgeBases.map((kb) => {
                      const isSelected = selectedKbIds.includes(kb.id);
                      return (
                        <div
                          key={kb.id}
                          onClick={() => toggleKbSelection(kb.id)}
                          className={`flex items-center justify-between p-2.5 rounded-lg border cursor-pointer transition-all ${
                            isSelected
                              ? 'bg-indigo-950/40 border-indigo-500/50 text-white'
                              : 'bg-slate-900/40 border-slate-800 text-slate-300 hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-center gap-2.5">
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-indigo-400 shrink-0" />
                            ) : (
                              <Square className="w-4 h-4 text-slate-500 shrink-0" />
                            )}
                            <div>
                              <p className="text-xs font-medium leading-tight">{kb.name}</p>
                              {kb.description && (
                                <p className="text-[10px] text-slate-400 line-clamp-1">
                                  {kb.description}
                                </p>
                              )}
                            </div>
                          </div>
                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded font-mono ${
                              isSelected
                                ? 'bg-indigo-500/20 text-indigo-300'
                                : 'bg-slate-800 text-slate-500'
                            }`}
                          >
                            {isSelected ? 'ACCESS GRANTED' : 'NO ACCESS'}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* TOOL CAPABILITIES ACCESS CHECKLIST */}
              <div className="p-3.5 rounded-lg bg-slate-800/50 border border-slate-700/80 space-y-2.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                    <Wrench className="w-4 h-4 text-emerald-400" />
                    Agent Capabilities & Tools (Action Boundary)
                  </label>
                  {allTools.length > 0 && (
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={selectAllTools}
                        className="text-[11px] text-emerald-400 hover:text-emerald-300 font-medium"
                      >
                        Select All
                      </button>
                      <span className="text-slate-600">•</span>
                      <button
                        type="button"
                        onClick={clearAllTools}
                        className="text-[11px] text-slate-400 hover:text-slate-300"
                      >
                        Clear
                      </button>
                    </div>
                  )}
                </div>

                <p className="text-[11px] text-slate-400">
                  Select tools this employee can execute. READ actions run automatically; WRITE actions require human confirmation. Unassigned tools cannot be invoked.
                </p>

                {allTools.length === 0 ? (
                  <div className="text-center py-3 bg-slate-900/60 rounded-lg border border-dashed border-slate-800 text-xs text-slate-400">
                    No tools registered in the platform yet.
                  </div>
                ) : (
                  <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                    {allTools.map((t) => {
                      const isSelected = selectedToolNames.includes(t.name);
                      const isWrite = t.permission === 'WRITE';
                      return (
                        <div
                          key={t.name}
                          onClick={() => toggleToolSelection(t.name)}
                          className={`flex items-start justify-between p-2.5 rounded-lg border cursor-pointer transition-all ${
                            isSelected
                              ? 'bg-emerald-950/30 border-emerald-500/50 text-white'
                              : 'bg-slate-900/40 border-slate-800 text-slate-300 hover:border-slate-700'
                          }`}
                        >
                          <div className="flex items-start gap-2.5">
                            {isSelected ? (
                              <CheckSquare className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                            ) : (
                              <Square className="w-4 h-4 text-slate-500 shrink-0 mt-0.5" />
                            )}
                            <div>
                              <div className="flex items-center gap-2">
                                <p className="text-xs font-mono font-semibold text-emerald-300">{t.name}</p>
                                <span
                                  className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase tracking-wider ${
                                    isWrite
                                      ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                      : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30'
                                  }`}
                                >
                                  {isWrite ? 'Write • Confirmation' : 'Read • Auto'}
                                </span>
                              </div>
                              <p className="text-[10px] text-slate-400 mt-0.5 leading-snug">
                                {t.description}
                              </p>
                            </div>
                          </div>
                          <span
                            className={`text-[9px] px-1.5 py-0.5 rounded font-mono shrink-0 ml-2 ${
                              isSelected
                                ? 'bg-emerald-500/20 text-emerald-300'
                                : 'bg-slate-800 text-slate-500'
                            }`}
                          >
                            {isSelected ? 'ENABLED' : 'DISABLED'}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
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
                    <option value="hi">Hindi (hi)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Deployment Status
                  </label>
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

              <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors shadow-lg shadow-indigo-500/20"
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
