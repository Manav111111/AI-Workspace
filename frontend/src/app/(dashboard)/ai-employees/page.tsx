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
  Globe,
  Code,
  Copy,
  ExternalLink,
  Check,
  Palette,
  Eye,
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

  // Phase 5: Voice Configuration Form State
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [voiceId, setVoiceId] = useState('alloy');
  const [voiceSpeed, setVoiceSpeed] = useState(1.0);
  const [availableVoices, setAvailableVoices] = useState<import('@/types').VoiceDefinition[]>([]);

  // Phase 4: Embed & Widget Customization Modal State
  const [isEmbedModalOpen, setIsEmbedModalOpen] = useState(false);
  const [activeEmbedEmployee, setActiveEmbedEmployee] = useState<AIEmployee | null>(null);
  const [embedData, setEmbedData] = useState<import('@/types').EmployeeEmbedCodeResponse | null>(null);
  const [activeEmbedTab, setActiveEmbedTab] = useState<'snippet' | 'customizer' | 'domains' | 'preview'>('snippet');
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [isTogglingPublish, setIsTogglingPublish] = useState<string | null>(null);

  // Widget Customizer Form State
  const [widgetPrimaryColor, setWidgetPrimaryColor] = useState('#4f46e5');
  const [widgetTheme, setWidgetTheme] = useState('dark');
  const [widgetPosition, setWidgetPosition] = useState('bottom-right');
  const [widgetBrandName, setWidgetBrandName] = useState('');
  const [widgetWelcomeMsg, setWidgetWelcomeMsg] = useState('Hi! How can I help you today?');
  const [allowedDomainsList, setAllowedDomainsList] = useState<string[]>([]);
  const [newDomainInput, setNewDomainInput] = useState('');
  const [domainError, setDomainError] = useState<string | null>(null);
  const [isSavingWidgetConfig, setIsSavingWidgetConfig] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [empData, kbData, toolData, voiceData] = await Promise.all([
        api.getAIEmployees(),
        api.getKnowledgeBases().catch(() => []),
        api.getTools().catch(() => []),
        api.getAvailableVoices().catch(() => ({ provider: 'mock', voices: [] })),
      ]);
      setEmployees(empData);
      setAllKnowledgeBases(kbData);
      setAllTools(toolData);
      if (voiceData && voiceData.voices) {
        setAvailableVoices(voiceData.voices);
      }
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
    setVoiceEnabled(true);
    setVoiceId(availableVoices.length > 0 ? availableVoices[0].id : 'alloy');
    setVoiceSpeed(1.0);
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

    const vConfig = emp.voice_config || {};
    setVoiceEnabled(vConfig.enabled !== false);
    setVoiceId(vConfig.voice_id || (availableVoices.length > 0 ? availableVoices[0].id : 'alloy'));
    setVoiceSpeed(typeof vConfig.speed === 'number' ? vConfig.speed : 1.0);
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
      voice_config: {
        enabled: voiceEnabled,
        voice_id: voiceId,
        speed: voiceSpeed,
      },
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

  // Phase 4: Publish / Unpublish Toggle Action
  const handleTogglePublish = async (emp: AIEmployee) => {
    setIsTogglingPublish(emp.id);
    setError(null);
    setSuccess(null);
    try {
      if (emp.is_published) {
        await api.unpublishAIEmployee(emp.id);
        setSuccess(`Unpublished "${emp.name}". Public website widget access disabled.`);
      } else {
        await api.publishAIEmployee(emp.id, {
          is_published: true,
          allowed_domains: emp.allowed_domains || [],
        });
        setSuccess(`Published "${emp.name}". Public website widget is now active!`);
      }
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to toggle publish status');
    } finally {
      setIsTogglingPublish(null);
    }
  };

  // Phase 4: Open Embed & Customizer Modal
  const openEmbedModal = async (emp: AIEmployee) => {
    setActiveEmbedEmployee(emp);
    setError(null);
    setSuccess(null);
    setCopiedSnippet(false);
    setDomainError(null);
    setActiveEmbedTab('snippet');

    // Populate widget configuration defaults from employee
    const wConfig = emp.widget_config || {};
    setWidgetPrimaryColor(wConfig.primary_color || '#4f46e5');
    setWidgetTheme(wConfig.theme || 'dark');
    setWidgetPosition(wConfig.position || 'bottom-right');
    setWidgetBrandName(wConfig.brand_name || emp.name);
    setWidgetWelcomeMsg(wConfig.welcome_message || `Hi! I am ${emp.name}. How can I help you today?`);
    setAllowedDomainsList(emp.allowed_domains || []);

    try {
      const data = await api.getAIEmployeeEmbed(emp.id);
      setEmbedData(data);
      setIsEmbedModalOpen(true);
    } catch (err: any) {
      setError(err.message || 'Failed to load embed snippet');
    }
  };

  // Phase 4: Copy Snippet to Clipboard
  const handleCopySnippet = async () => {
    if (!embedData?.embed_snippet) return;
    try {
      await navigator.clipboard.writeText(embedData.embed_snippet);
      setCopiedSnippet(true);
      setTimeout(() => setCopiedSnippet(false), 2500);
    } catch (err) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = embedData.embed_snippet;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      setCopiedSnippet(true);
      setTimeout(() => setCopiedSnippet(false), 2500);
    }
  };

  // Phase 4: Add Allowed Domain with Validation
  const handleAddDomain = () => {
    setDomainError(null);
    const domain = newDomainInput.trim().toLowerCase();
    if (!domain) return;

    // Clean protocol or path if user pasted full URL
    let clean = domain.replace(/^https?:\/\//, '').replace(/\/.*$/, '').trim();

    // Regex validation for hostname / domain format
    const domainRegex = /^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$|^localhost(:[0-9]+)?$/i;
    if (!domainRegex.test(clean)) {
      setDomainError('Please enter a valid domain (e.g. example.com, app.example.com, or localhost:3000)');
      return;
    }

    if (allowedDomainsList.includes(clean)) {
      setDomainError('Domain is already in the allowed list');
      return;
    }

    setAllowedDomainsList([...allowedDomainsList, clean]);
    setNewDomainInput('');
  };

  const handleRemoveDomain = (domainToRemove: string) => {
    setAllowedDomainsList(allowedDomainsList.filter((d) => d !== domainToRemove));
  };

  // Phase 4: Save Widget Configuration & Allowed Domains
  const handleSaveWidgetConfig = async () => {
    if (!activeEmbedEmployee) return;
    setIsSavingWidgetConfig(true);
    setError(null);
    try {
      const updated = await api.updateAIEmployeeWidgetConfig(activeEmbedEmployee.id, {
        primary_color: widgetPrimaryColor,
        theme: widgetTheme,
        position: widgetPosition,
        brand_name: widgetBrandName,
        welcome_message: widgetWelcomeMsg,
        allowed_domains: allowedDomainsList,
      });

      setActiveEmbedEmployee(updated);
      const refreshEmbed = await api.getAIEmployeeEmbed(activeEmbedEmployee.id);
      setEmbedData(refreshEmbed);
      setSuccess('Widget customization and allowed domains saved successfully!');
      await loadData();
    } catch (err: any) {
      setError(err.message || 'Failed to save widget configuration');
    } finally {
      setIsSavingWidgetConfig(false);
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

                  <div className="flex items-center gap-1.5">
                    {/* Deployment Status */}
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-semibold tracking-wider ${
                        emp.status === 'ACTIVE'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {emp.status}
                    </span>

                    {/* Phase 4: Publishing Status Badge */}
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded font-semibold tracking-wider flex items-center gap-1 ${
                        emp.is_published
                          ? 'bg-sky-500/15 text-sky-400 border border-sky-500/30'
                          : 'bg-slate-800/80 text-slate-500 border border-slate-700/50'
                      }`}
                    >
                      <Globe className="w-2.5 h-2.5" />
                      {emp.is_published ? 'PUBLISHED' : 'UNPUBLISHED'}
                    </span>
                  </div>

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

              <div className="mt-5 pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
                <div className="flex items-center gap-2">
                  <Link
                    href={`/ai-employees/${emp.id}/chat`}
                    className="px-3 py-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-300 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-colors"
                  >
                    <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Chat</span>
                  </Link>

                  {/* Phase 4: Embed & Widget Configuration Button */}
                  <button
                    onClick={() => openEmbedModal(emp)}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 hover:text-white text-xs font-medium flex items-center gap-1.5 transition-colors"
                    title="Get Embed Code and Customize Widget"
                  >
                    <Code className="w-3.5 h-3.5 text-sky-400" />
                    <span>Embed & Widget</span>
                  </button>
                </div>

                <div className="flex items-center justify-between sm:justify-end gap-2">
                  {/* Phase 4: Publish / Unpublish Toggle Action */}
                  <button
                    onClick={() => handleTogglePublish(emp)}
                    disabled={isTogglingPublish === emp.id}
                    className={`px-2.5 py-1.5 rounded-lg text-xs font-medium border flex items-center gap-1.5 transition-all ${
                      emp.is_published
                        ? 'bg-rose-950/40 hover:bg-rose-900/60 border-rose-800/60 text-rose-300'
                        : 'bg-emerald-950/40 hover:bg-emerald-900/60 border-emerald-800/60 text-emerald-300'
                    } disabled:opacity-50`}
                    title={emp.is_published ? 'Disable public website widget access' : 'Enable public website widget access'}
                  >
                    <Globe className="w-3.5 h-3.5" />
                    <span>
                      {isTogglingPublish === emp.id
                        ? 'Updating...'
                        : emp.is_published
                        ? 'Unpublish'
                        : 'Publish'}
                    </span>
                  </button>

                  <div className="flex items-center gap-1">
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

              {/* PHASE 5: VOICE AI CONFIGURATION */}
              <div className="p-3.5 rounded-lg bg-slate-800/50 border border-slate-700/80 space-y-3">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                    <Volume2 className="w-4 h-4 text-violet-400" />
                    Voice AI Interface (STT & TTS)
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={voiceEnabled}
                      onChange={(e) => setVoiceEnabled(e.target.checked)}
                      className="sr-only"
                    />
                    <div className={`w-8 h-4 rounded-full transition-colors relative ${voiceEnabled ? 'bg-violet-600' : 'bg-slate-700'}`}>
                      <div className={`w-3 h-3 rounded-full bg-white absolute top-0.5 transition-transform ${voiceEnabled ? 'left-4.5' : 'left-0.5'}`} />
                    </div>
                    <span className="text-[11px] text-slate-300 font-medium">
                      {voiceEnabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </label>
                </div>

                <p className="text-[11px] text-slate-400">
                  Enables real-time bidirectional voice conversations via widget using the identical AI Employee brain, knowledge bases, and tools.
                </p>

                {voiceEnabled && (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                    <div>
                      <label className="block text-[11px] font-medium text-slate-300 mb-1">
                        Synthesized Voice
                      </label>
                      <select
                        value={voiceId}
                        onChange={(e) => setVoiceId(e.target.value)}
                        className="w-full px-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:ring-2 focus:ring-violet-500"
                      >
                        {availableVoices.length > 0 ? (
                          availableVoices.map((v) => (
                            <option key={v.id} value={v.id}>
                              {v.name} ({v.gender || 'neutral'})
                            </option>
                          ))
                        ) : (
                          <>
                            <option value="alloy">Alloy (neutral)</option>
                            <option value="echo">Echo (male)</option>
                            <option value="fable">Fable (female)</option>
                            <option value="onyx">Onyx (male)</option>
                            <option value="nova">Nova (female)</option>
                            <option value="shimmer">Shimmer (female)</option>
                          </>
                        )}
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-medium text-slate-300 mb-1">
                        Speech Rate ({voiceSpeed}x)
                      </label>
                      <input
                        type="range"
                        min="0.8"
                        max="1.2"
                        step="0.05"
                        value={voiceSpeed}
                        onChange={(e) => setVoiceSpeed(parseFloat(e.target.value))}
                        className="w-full accent-violet-500 cursor-pointer mt-1"
                      />
                    </div>
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

      {/* Phase 4: Embed & Widget Customizer Modal */}
      {isEmbedModalOpen && activeEmbedEmployee && (
        <div className="fixed inset-0 bg-black/75 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl p-6 shadow-2xl max-h-[92vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400 flex items-center justify-center">
                  <Code className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-white flex items-center gap-2">
                    <span>Embed & Widget Configuration</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-sky-950 text-sky-300 font-normal border border-sky-800/40">
                      {activeEmbedEmployee.name}
                    </span>
                  </h2>
                  <p className="text-xs text-slate-400">
                    Deploy your AI Employee to any website via a standalone snippet.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsEmbedModalOpen(false)}
                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Publishing Warning Banner if Unpublished */}
            {!activeEmbedEmployee.is_published && (
              <div className="mt-4 p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-between gap-3 text-xs text-amber-300">
                <div className="flex items-center gap-2.5">
                  <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>
                    This AI Employee is currently <strong>UNPUBLISHED</strong>. Public visitors cannot interact with the widget until published.
                  </span>
                </div>
                <button
                  onClick={() => handleTogglePublish(activeEmbedEmployee)}
                  className="px-3 py-1 bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold rounded-lg shrink-0 transition-colors"
                >
                  Publish Now
                </button>
              </div>
            )}

            {/* Navigation Tabs */}
            <div className="flex items-center gap-2 mt-4 border-b border-slate-800 pb-2">
              <button
                onClick={() => setActiveEmbedTab('snippet')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${
                  activeEmbedTab === 'snippet'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <Code className="w-3.5 h-3.5" />
                <span>Embed Code</span>
              </button>
              <button
                onClick={() => setActiveEmbedTab('customizer')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${
                  activeEmbedTab === 'customizer'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <Palette className="w-3.5 h-3.5" />
                <span>Theme & Widget</span>
              </button>
              <button
                onClick={() => setActiveEmbedTab('domains')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${
                  activeEmbedTab === 'domains'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                <span>Allowed Domains ({allowedDomainsList.length})</span>
              </button>
              <button
                onClick={() => setActiveEmbedTab('preview')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${
                  activeEmbedTab === 'preview'
                    ? 'bg-indigo-600 text-white'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Live Test Preview</span>
              </button>
            </div>

            {/* Modal Body / Tab Contents */}
            <div className="mt-4 flex-1 overflow-y-auto pr-1">
              {/* TAB 1: EMBED SNIPPET */}
              {activeEmbedTab === 'snippet' && (
                <div className="space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold text-slate-200 mb-1">
                      HTML Embed Snippet
                    </h3>
                    <p className="text-xs text-slate-400">
                      Paste this script into the <code className="text-indigo-300">&lt;head&gt;</code> or bottom of the <code className="text-indigo-300">&lt;body&gt;</code> tag on your website.
                    </p>
                  </div>

                  <div className="relative group">
                    <pre className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs font-mono text-indigo-300 overflow-x-auto whitespace-pre leading-relaxed">
                      {embedData?.embed_snippet || 'Loading embed code...'}
                    </pre>
                    <button
                      onClick={handleCopySnippet}
                      className="absolute top-3 right-3 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium flex items-center gap-1.5 shadow-lg transition-all"
                    >
                      {copiedSnippet ? (
                        <>
                          <Check className="w-3.5 h-3.5 text-emerald-300" />
                          <span>Copied!</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span>Copy Snippet</span>
                        </>
                      )}
                    </button>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 text-xs text-slate-400 space-y-2">
                    <div className="font-semibold text-slate-300 flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      <span>Security & Zero-Config Runtime</span>
                    </div>
                    <ul className="list-disc list-inside space-y-1 text-slate-400">
                      <li>Requires zero React or framework dependencies on the client site.</li>
                      <li>Encapsulated via <strong>Shadow DOM</strong> so styling will not bleed into or conflict with the host site.</li>
                      <li>Anonymous visitors authenticate via ephemeral Bearer headers with rate limits.</li>
                    </ul>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <span className="text-xs text-slate-500 font-mono">
                      Public ID: {embedData?.public_id || 'Generating...'}
                    </span>
                    {embedData?.public_id && (
                      <a
                        href={`/preview/${embedData.public_id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                      >
                        <span>Open Standalone Preview</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              )}

              {/* TAB 2: WIDGET CUSTOMIZER */}
              {activeEmbedTab === 'customizer' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Brand Name / Title
                      </label>
                      <input
                        type="text"
                        value={widgetBrandName}
                        onChange={(e) => setWidgetBrandName(e.target.value)}
                        placeholder={activeEmbedEmployee.name}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Brand Accent Color
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="color"
                          value={widgetPrimaryColor}
                          onChange={(e) => setWidgetPrimaryColor(e.target.value)}
                          className="w-10 h-8 rounded bg-transparent border-0 cursor-pointer"
                        />
                        <input
                          type="text"
                          value={widgetPrimaryColor}
                          onChange={(e) => setWidgetPrimaryColor(e.target.value)}
                          className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs font-mono text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Welcome Message
                    </label>
                    <input
                      type="text"
                      value={widgetWelcomeMsg}
                      onChange={(e) => setWidgetWelcomeMsg(e.target.value)}
                      placeholder="Hi! How can I help you today?"
                      className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Widget Position
                      </label>
                      <select
                        value={widgetPosition}
                        onChange={(e) => setWidgetPosition(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="bottom-right">Bottom Right (Default)</option>
                        <option value="bottom-left">Bottom Left</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Theme Mode
                      </label>
                      <select
                        value={widgetTheme}
                        onChange={(e) => setWidgetTheme(e.target.value)}
                        className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      >
                        <option value="dark">Dark Theme</option>
                        <option value="light">Light Theme</option>
                      </select>
                    </div>
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      onClick={handleSaveWidgetConfig}
                      disabled={isSavingWidgetConfig}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg shadow-lg shadow-indigo-500/20 transition-all flex items-center gap-1.5"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>{isSavingWidgetConfig ? 'Saving...' : 'Save Widget Customization'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 3: ALLOWED DOMAINS */}
              {activeEmbedTab === 'domains' && (
                <div className="space-y-4">
                  <div className="p-3.5 rounded-xl bg-indigo-950/30 border border-indigo-800/40 text-xs text-indigo-300 leading-relaxed">
                    <strong>Integration Boundary Notice:</strong> Domain restrictions prevent unauthorized external sites from embedding this AI employee widget. Note that domain validation is an integration control, while ephemeral sessions and rate limiting enforce visitor runtime security.
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Add Allowed Domain
                    </label>
                    <div className="flex items-center gap-2">
                      <input
                        type="text"
                        value={newDomainInput}
                        onChange={(e) => {
                          setNewDomainInput(e.target.value);
                          setDomainError(null);
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            handleAddDomain();
                          }
                        }}
                        placeholder="e.g. yourcompany.com, app.example.com, or localhost:3000"
                        className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                      <button
                        type="button"
                        onClick={handleAddDomain}
                        className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-white font-medium rounded-lg transition-colors flex items-center gap-1"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add</span>
                      </button>
                    </div>
                    {domainError && (
                      <p className="mt-1.5 text-xs text-rose-400">{domainError}</p>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-slate-300">
                        Active Allowed Domains
                      </span>
                      <span className="text-[11px] text-slate-500 font-mono">
                        {allowedDomainsList.length === 0
                          ? 'Open mode (all origins allowed)'
                          : `${allowedDomainsList.length} domain(s) configured`}
                      </span>
                    </div>

                    {allowedDomainsList.length === 0 ? (
                      <div className="p-4 rounded-xl bg-slate-950/60 border border-dashed border-slate-800 text-center text-xs text-slate-400">
                        No domains specified. The widget will accept requests from any origin (recommended for development & testing).
                      </div>
                    ) : (
                      <div className="space-y-1.5 max-h-48 overflow-y-auto">
                        {allowedDomainsList.map((d) => (
                          <div
                            key={d}
                            className="flex items-center justify-between p-2.5 rounded-lg bg-slate-800/60 border border-slate-700/60 text-xs"
                          >
                            <span className="font-mono text-slate-200">{d}</span>
                            <button
                              type="button"
                              onClick={() => handleRemoveDomain(d)}
                              className="text-slate-400 hover:text-rose-400 transition-colors"
                              title="Remove domain"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="pt-2 flex justify-end">
                    <button
                      onClick={handleSaveWidgetConfig}
                      disabled={isSavingWidgetConfig}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg shadow-lg shadow-indigo-500/20 transition-all flex items-center gap-1.5"
                    >
                      <Check className="w-3.5 h-3.5" />
                      <span>{isSavingWidgetConfig ? 'Saving...' : 'Save Allowed Domains'}</span>
                    </button>
                  </div>
                </div>
              )}

              {/* TAB 4: LIVE PREVIEW */}
              {activeEmbedTab === 'preview' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-semibold text-slate-200">
                        Interactive Live Widget Preview
                      </h4>
                      <p className="text-[11px] text-slate-400">
                        Simulating an external website with the widget script loaded.
                      </p>
                    </div>
                    {embedData?.preview_url && (
                      <a
                        href={embedData.preview_url}
                        target="_blank"
                        rel="noreferrer"
                        className="px-3 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                      >
                        <span>Full Page Preview</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>

                  <div className="w-full h-96 rounded-xl border border-slate-800 bg-slate-950 overflow-hidden relative">
                    {embedData?.public_id ? (
                      <iframe
                        src={`/preview/${embedData.public_id}`}
                        className="w-full h-full border-0"
                        title="Widget Preview"
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full text-xs text-slate-500">
                        Generating preview frame...
                      </div>
                    )}
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

