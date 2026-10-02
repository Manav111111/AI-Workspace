'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api';
import { AIEmployee, AIEmployeeStatus, KnowledgeBase, ToolDefinition } from '@/types';
import {
  Bot,
  Plus,
  Trash2,
  Edit2,
  AlertCircle,
  CheckCircle2,
  X,
  Volume2,
  MessageSquare,
  BookOpen,
  ShieldAlert,
  Layers,
  CheckSquare,
  Square,
  Wrench,
  ShieldCheck,
  Globe,
  Code,
  Copy,
  ExternalLink,
  Check,
  Palette,
  Eye,
  User,
  Sparkles,
  ChevronRight,
  ChevronLeft,
  Sliders,
  Cpu,
  FileText,
} from 'lucide-react';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Card, CardContent } from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';

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
  const [wizardStep, setWizardStep] = useState<number>(1);
  const [name, setName] = useState('');
  const [role, setRole] = useState('');
  const [description, setDescription] = useState('');
  const [personality, setPersonality] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [language, setLanguage] = useState('en');
  const [status, setStatus] = useState<AIEmployeeStatus>('DRAFT');
  const [selectedKbIds, setSelectedKbIds] = useState<string[]>([]);
  const [selectedToolNames, setSelectedToolNames] = useState<string[]>([]);
  const [aiModel, setAiModel] = useState('gemini-3.5-flash');
  const [temperature, setTemperature] = useState(0.2);
  const [topK, setTopK] = useState(5);

  // Voice & Avatar legacy compatibility fields (Defaulted safely without cluttering UI)
  const [voiceEnabled, setVoiceEnabled] = useState(false);
  const [voiceId, setVoiceId] = useState('alloy');
  const [voiceSpeed, setVoiceSpeed] = useState(1.0);
  const [availableVoices, setAvailableVoices] = useState<import('@/types').VoiceDefinition[]>([]);
  const [avatarEnabled, setAvatarEnabled] = useState(false);
  const [avatarPreset, setAvatarPreset] = useState('executive_sarah');
  const [avatarExpression, setAvatarExpression] = useState('approachable');
  const [avatarFraming, setAvatarFraming] = useState('bust');

  // Embed & Widget Customization Modal State
  const [isEmbedModalOpen, setIsEmbedModalOpen] = useState(false);
  const [activeEmbedEmployee, setActiveEmbedEmployee] = useState<AIEmployee | null>(null);
  const [embedData, setEmbedData] = useState<import('@/types').EmployeeEmbedCodeResponse | null>(null);
  const [activeEmbedTab, setActiveEmbedTab] = useState<'snippet' | 'customizer' | 'domains' | 'preview'>('snippet');
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [isTogglingPublish, setIsTogglingPublish] = useState<string | null>(null);

  // Widget Customizer Form State
  const [widgetPrimaryColor, setWidgetPrimaryColor] = useState('#FF9D00');
  const [widgetTheme, setWidgetTheme] = useState('dark');
  const [widgetPosition, setWidgetPosition] = useState('bottom-right');
  const [widgetBrandName, setWidgetBrandName] = useState('');
  const [widgetWelcomeMsg, setWidgetWelcomeMsg] = useState('Hi! How can I help you today?');
  const [allowedDomainsList, setAllowedDomainsList] = useState<string[]>([]);
  const [newDomainInput, setNewDomainInput] = useState('');
  const [domainError, setDomainError] = useState<string | null>(null);
  const [isSavingWidgetConfig, setIsSavingWidgetConfig] = useState(false);
  const [isSavingEmployee, setIsSavingEmployee] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);

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
    setError(null);
    setModalError(null);
    setWizardStep(1);
    setName('');
    setRole('');
    setDescription('');
    setPersonality('Professional, authoritative, empathetic, concise');
    setSystemPrompt('You are an enterprise AI Employee. Answer user questions grounded strictly in retrieved knowledge base documentation. Always include accurate citations.');
    setLanguage('en');
    setStatus('DRAFT');
    setSelectedKbIds([]);
    setSelectedToolNames(['product_search', 'order_lookup']);
    setAiModel('gemini-3.5-flash');
    setTemperature(0.2);
    setTopK(5);
    setVoiceEnabled(false);
    setAvatarEnabled(false);
    setIsModalOpen(true);
  };

  const openEditModal = (emp: AIEmployee) => {
    setEditingEmployee(emp);
    setError(null);
    setModalError(null);
    setWizardStep(1);
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
    setAiModel('gemini-3.5-flash');
    setTemperature(0.2);
    setTopK(5);
    setVoiceEnabled(false);
    setAvatarEnabled(false);
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

  const handleNextStep = () => {
    setModalError(null);
    if (wizardStep === 1) {
      if (!name.trim() || !role.trim()) {
        setModalError('Please enter both Employee Name and Role to continue.');
        return;
      }
    }
    if (wizardStep < 6) {
      setWizardStep((prev) => prev + 1);
    }
  };

  const handleSave = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    setError(null);
    setModalError(null);
    setSuccess(null);

    const trimmedName = name.trim();
    const trimmedRole = role.trim();

    if (!trimmedName || !trimmedRole) {
      setModalError('Please enter both Employee Name and Role.');
      setWizardStep(1);
      return;
    }

    setIsSavingEmployee(true);

    const payload: any = {
      name: trimmedName,
      role: trimmedRole,
      description: description.trim() || undefined,
      personality: personality.trim() || undefined,
      system_prompt: systemPrompt.trim() || undefined,
      language,
      status,
      knowledge_base_ids: selectedKbIds,
      tools: selectedToolNames,
      voice_config: {
        enabled: voiceEnabled,
        voice_id: voiceId,
        speed: voiceSpeed,
      },
      avatar_config: {
        enabled: avatarEnabled,
        model_preset: avatarPreset,
        expression: avatarExpression,
        framing: avatarFraming,
      },
    };

    try {
      if (editingEmployee) {
        await api.updateAIEmployee(editingEmployee.id, payload);
        setSuccess(`Updated AI Employee "${trimmedName}" with ${selectedKbIds.length} KBs and ${selectedToolNames.length} tools.`);
      } else {
        await api.createAIEmployee(payload);
        setSuccess(`Created AI Employee "${trimmedName}" with ${selectedKbIds.length} KBs and ${selectedToolNames.length} tools.`);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      setModalError(err.message || 'Failed to save AI employee');
    } finally {
      setIsSavingEmployee(false);
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

  const openEmbedModal = async (emp: AIEmployee) => {
    setActiveEmbedEmployee(emp);
    setError(null);
    setSuccess(null);
    setCopiedSnippet(false);
    setDomainError(null);
    setActiveEmbedTab('snippet');

    const wConfig = emp.widget_config || {};
    setWidgetPrimaryColor(wConfig.primary_color || '#FF9D00');
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

  const handleCopySnippet = async () => {
    if (!embedData?.embed_snippet) return;
    try {
      await navigator.clipboard.writeText(embedData.embed_snippet);
      setCopiedSnippet(true);
      setTimeout(() => setCopiedSnippet(false), 2500);
    } catch (err) {
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

  const handleAddDomain = () => {
    setDomainError(null);
    const domain = newDomainInput.trim().toLowerCase();
    if (!domain) return;

    let clean = domain.replace(/^https?:\/\//, '').replace(/\/.*$/, '').trim();
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
    <div className="max-w-7xl mx-auto space-y-7 font-sans">
      {/* Page Header */}
      <PageHeader
        title="AI Employees"
        description="Configure personas, system directives, assigned knowledge base retrieval scopes, and agent tool execution permissions."
        badge={<Badge variant="orange">Role &amp; Knowledge Scoped</Badge>}
        actions={
          <Button variant="primary" size="sm" icon={Plus} onClick={openCreateModal}>
            Create AI Employee
          </Button>
        }
      />

      {/* Alerts */}
      {error && (
        <div className="p-3.5 rounded-xl bg-rose-950/60 border border-rose-800/50 flex items-center gap-3 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="p-3.5 rounded-xl bg-emerald-950/60 border border-emerald-800/50 flex items-center gap-3 text-emerald-300 text-xs">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {/* Grid of Employees */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="h-64 rounded-xl bg-[#101010] border border-[#262626] animate-pulse"
            />
          ))}
        </div>
      ) : employees.length === 0 ? (
        <EmptyState
          icon={Bot}
          title="No AI Employees yet"
          description="Create your first AI employee and configure its assigned knowledge bases and action tools."
          actionText="Create AI Employee"
          actionIcon={Plus}
          onAction={openCreateModal}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {employees.map((emp) => (
            <Card key={emp.id} hover className="flex flex-col justify-between">
              <CardContent className="p-5">
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] shrink-0">
                        <Bot className="w-5 h-5" />
                      </div>
                      <div>
                        <h3 className="font-display font-semibold text-[#F5F5F5] text-sm tracking-tight">{emp.name}</h3>
                        <p className="text-xs text-[#FF9D00] font-mono mt-0.5">{emp.role}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <Badge variant={emp.status === 'ACTIVE' ? 'forest' : 'neutral'} dot>
                        {emp.status}
                      </Badge>
                      <Badge variant={emp.is_published ? 'orange' : 'outline'}>
                        {emp.is_published ? 'Published' : 'Draft'}
                      </Badge>
                    </div>
                  </div>

                  {emp.description && (
                    <p className="mt-3 text-xs text-[#737373] line-clamp-2 leading-relaxed font-sans">
                      {emp.description}
                    </p>
                  )}

                  {emp.personality && (
                    <div className="mt-3 p-2.5 rounded-lg bg-[#151515] border border-[#262626] text-xs">
                      <span className="font-medium text-[#A1A1AA]">Personality: </span>
                      <span className="text-[#737373]">{emp.personality}</span>
                    </div>
                  )}

                  {/* Scoped Knowledge Access Badge Section */}
                  <div className="mt-3.5 pt-3 border-t border-[#262626]">
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="text-[#A1A1AA] font-medium flex items-center gap-1.5">
                        <BookOpen className="w-3.5 h-3.5 text-[#FF9D00]" />
                        Knowledge Scope:
                      </span>
                      <span className="text-[11px] text-[#737373] font-mono">
                        {emp.assigned_knowledge_bases?.length || 0} assigned
                      </span>
                    </div>

                    {emp.assigned_knowledge_bases && emp.assigned_knowledge_bases.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 mt-1.5">
                        {emp.assigned_knowledge_bases.map((kb) => (
                          <span
                            key={kb.id}
                            className="px-2 py-0.5 rounded-md bg-[#151515] border border-[#262626] text-[#F5F5F5] text-[11px] font-medium flex items-center gap-1"
                          >
                            <Layers className="w-2.5 h-2.5 text-[#FF9D00]" />
                            {kb.name}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <div className="text-[11px] text-[#FFC247] bg-orange-950/40 border border-orange-800/50 px-2 py-1 rounded flex items-center gap-1.5 mt-1">
                        <ShieldAlert className="w-3 h-3 text-[#FF9D00] shrink-0" />
                        <span>No knowledge assigned (Pure Persona)</span>
                      </div>
                    )}
                  </div>

                  {/* Assigned Tool Capabilities Badge Section */}
                  <div className="mt-2.5 pt-2.5 border-t border-[#262626]">
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <span className="text-[#A1A1AA] font-medium flex items-center gap-1.5">
                        <Wrench className="w-3.5 h-3.5 text-[#FF9D00]" />
                        Assigned Tools:
                      </span>
                      <span className="text-[11px] text-[#737373] font-mono">
                        {emp.tools?.length || emp.assigned_tools?.length || 0} active
                      </span>
                    </div>

                    {(emp.tools && emp.tools.length > 0) || (emp.assigned_tools && emp.assigned_tools.length > 0) ? (
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {(emp.tools || emp.assigned_tools?.map((t) => t.tool_name) || []).map((toolName) => (
                          <span
                            key={toolName}
                            className="px-2 py-0.5 rounded-md bg-[#151515] border border-[#262626] text-[#A1A1AA] text-[10px] font-mono flex items-center gap-1"
                          >
                            <ShieldCheck className="w-2.5 h-2.5 text-[#FF9D00]" />
                            {toolName}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <div className="text-[11px] text-[#737373] bg-[#151515] border border-[#262626] px-2 py-0.5 rounded flex items-center gap-1.5 mt-1">
                        <span>Read-only conversation mode</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-5 pt-4 border-t border-[#262626] flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-2.5">
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/ai-employees/${emp.id}/chat`}
                      className="px-3 py-1.5 rounded-lg bg-[#151515] hover:bg-[#1A1A1A] border border-[#262626] hover:border-[#383838] text-[#F5F5F5] text-xs font-semibold flex items-center gap-1.5 transition-editorial"
                    >
                      <MessageSquare className="w-3.5 h-3.5 text-[#FF9D00]" />
                      <span>Chat</span>
                    </Link>

                    <button
                      onClick={() => openEmbedModal(emp)}
                      className="px-3 py-1.5 rounded-lg bg-[#151515] hover:bg-[#1A1A1A] border border-[#262626] hover:border-[#383838] text-[#F5F5F5] text-xs font-semibold flex items-center gap-1.5 transition-editorial"
                      title="Get Embed Code and Customize Widget"
                    >
                      <Code className="w-3.5 h-3.5 text-[#A1A1AA]" />
                      <span>Widget</span>
                    </button>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end gap-2">
                    <button
                      onClick={() => handleTogglePublish(emp)}
                      disabled={isTogglingPublish === emp.id}
                      className={`px-2.5 py-1.5 rounded-lg text-xs font-semibold border flex items-center gap-1.5 transition-editorial ${
                        emp.is_published
                          ? 'bg-rose-950/60 hover:bg-rose-900/80 border-rose-800/60 text-rose-300'
                          : 'bg-orange-950/60 hover:bg-orange-900/80 border-orange-800/60 text-[#FFC247]'
                      } disabled:opacity-50`}
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
                        className="p-1.5 text-[#737373] hover:text-[#F5F5F5] hover:bg-[#151515] rounded transition-editorial"
                        title="Edit Employee"
                      >
                        <Edit2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(emp.id, emp.name)}
                        className="p-1.5 text-[#737373] hover:text-rose-400 hover:bg-[#151515] rounded transition-editorial"
                        title="Delete Employee"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create / Edit Modal (Clean Chat-First 6-Step Wizard) */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-2xl p-6 shadow-card max-h-[92vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-[#262626] shrink-0">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] text-[#FF9D00] flex items-center justify-center">
                  <Bot className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-base font-display font-bold text-[#F5F5F5] flex items-center gap-2">
                    <span>{editingEmployee ? 'Edit AI Employee' : 'Create AI Employee'}</span>
                    <Badge variant="orange">Chatbot-First</Badge>
                  </h2>
                  <p className="text-xs text-[#737373]">
                    Configure identity, grounded knowledge base retrieval, and safe agent tools.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-[#737373] hover:text-[#F5F5F5] p-1.5 rounded-lg hover:bg-[#151515] transition-editorial"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* 6-Step Progress Bar Indicator */}
            <div className="grid grid-cols-6 gap-1.5 mt-4 pb-3 border-b border-[#262626] shrink-0">
              {[
                { step: 1, label: 'Identity', icon: User },
                { step: 2, label: 'Instructions', icon: FileText },
                { step: 3, label: 'Knowledge', icon: BookOpen },
                { step: 4, label: 'AI Model', icon: Cpu },
                { step: 5, label: 'Tools', icon: Wrench },
                { step: 6, label: 'Review', icon: CheckCircle2 },
              ].map((s) => {
                const isCurrent = wizardStep === s.step;
                const isPast = wizardStep > s.step;
                const StepIcon = s.icon;
                return (
                  <button
                    key={s.step}
                    type="button"
                    onClick={() => {
                      if (s.step < wizardStep || (name.trim() && role.trim())) {
                        setWizardStep(s.step);
                      }
                    }}
                    className={`p-2 rounded-lg text-left flex flex-col gap-1 transition-editorial ${
                      isCurrent
                        ? 'bg-orange-950/40 border border-[#FF9D00]/50 text-[#FFC247]'
                        : isPast
                        ? 'bg-[#151515] border border-[#262626] text-[#F5F5F5] hover:border-[#383838]'
                        : 'bg-[#0B0B0B] border border-[#1A1A1A] text-[#52525B]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-mono font-semibold">0{s.step}</span>
                      <StepIcon className="w-3 h-3" />
                    </div>
                    <span className="text-[11px] font-medium leading-none truncate">{s.label}</span>
                  </button>
                );
              })}
            </div>

            {modalError && (
              <div className="mt-3 p-3 rounded-lg bg-rose-950/60 border border-rose-800/50 flex items-center gap-2 text-rose-300 text-xs shrink-0">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{modalError}</span>
              </div>
            )}

            {/* Modal Body / Step Form */}
            <div className="mt-4 flex-1 overflow-y-auto pr-1 space-y-4">
              {/* STEP 1: IDENTITY */}
              {wizardStep === 1 && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                        Employee Name *
                      </label>
                      <input
                        type="text"
                        required
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="e.g. Sam, Maya, Alex"
                        className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40 focus:border-[#FF9D00]"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                        Role / Mandate *
                      </label>
                      <input
                        type="text"
                        required
                        value={role}
                        onChange={(e) => setRole(e.target.value)}
                        placeholder="e.g. AI Customer Specialist, HR Assistant"
                        className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40 focus:border-[#FF9D00]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                      Description
                    </label>
                    <input
                      type="text"
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Mandate and primary function within the organization"
                      className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40 focus:border-[#FF9D00]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                      Primary Language
                    </label>
                    <select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="w-full px-3 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40"
                    >
                      <option value="en">English (en)</option>
                      <option value="es">Spanish (es)</option>
                      <option value="fr">French (fr)</option>
                      <option value="de">German (de)</option>
                      <option value="hi">Hindi (hi)</option>
                    </select>
                  </div>
                </div>
              )}

              {/* STEP 2: INSTRUCTIONS */}
              {wizardStep === 2 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                      Personality &amp; Tone
                    </label>
                    <input
                      type="text"
                      value={personality}
                      onChange={(e) => setPersonality(e.target.value)}
                      placeholder="e.g. Professional, authoritative, empathetic, concise"
                      className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40 focus:border-[#FF9D00]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                      System Instructions (Prompt Directives)
                    </label>
                    <textarea
                      rows={6}
                      value={systemPrompt}
                      onChange={(e) => setSystemPrompt(e.target.value)}
                      placeholder="Define role behavioral boundaries, knowledge grounding rules, and fallback behavior..."
                      className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40 focus:border-[#FF9D00] font-mono leading-relaxed"
                    />
                    <p className="mt-1.5 text-[11px] text-[#737373]">
                      Retrieved company knowledge will be injected as grounded context with prompt injection resistance.
                    </p>
                  </div>
                </div>
              )}

              {/* STEP 3: KNOWLEDGE */}
              {wizardStep === 3 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-semibold text-[#F5F5F5]">
                        Scoped Knowledge Base Access
                      </h3>
                      <p className="text-[11px] text-[#737373]">
                        Select which knowledge collections this employee can retrieve from. Unselected knowledge is strictly isolated.
                      </p>
                    </div>
                    {allKnowledgeBases.length > 0 && (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={selectAllKbs}
                          className="text-[11px] text-[#FF9D00] hover:text-[#FF6A00] font-semibold"
                        >
                          Select All
                        </button>
                        <span className="text-[#262626]">•</span>
                        <button
                          type="button"
                          onClick={clearAllKbs}
                          className="text-[11px] text-[#737373] hover:text-[#A1A1AA]"
                        >
                          Clear
                        </button>
                      </div>
                    )}
                  </div>

                  {allKnowledgeBases.length === 0 ? (
                    <div className="text-center py-6 bg-[#151515] rounded-xl border border-dashed border-[#262626] text-xs text-[#737373]">
                      No knowledge bases created yet.{' '}
                      <Link href="/knowledge" className="text-[#FF9D00] hover:underline font-semibold">
                        Create a Knowledge Base
                      </Link>{' '}
                      to ground this AI Employee.
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {allKnowledgeBases.map((kb) => {
                        const isSelected = selectedKbIds.includes(kb.id);
                        return (
                          <div
                            key={kb.id}
                            onClick={() => toggleKbSelection(kb.id)}
                            className={`flex items-center justify-between p-3 rounded-lg border cursor-pointer transition-editorial ${
                              isSelected
                                ? 'bg-orange-950/30 border-orange-600/50 text-white'
                                : 'bg-[#151515] border-[#262626] text-[#A1A1AA] hover:border-[#383838]'
                            }`}
                          >
                            <div className="flex items-center gap-3">
                              {isSelected ? (
                                <CheckSquare className="w-4 h-4 text-[#FF9D00] shrink-0" />
                              ) : (
                                <Square className="w-4 h-4 text-[#737373] shrink-0" />
                              )}
                              <div>
                                <p className="text-xs font-semibold leading-tight">{kb.name}</p>
                                {kb.description && (
                                  <p className="text-[11px] text-[#737373] line-clamp-1 mt-0.5">
                                    {kb.description}
                                  </p>
                                )}
                              </div>
                            </div>
                            <Badge variant={isSelected ? 'orange' : 'outline'}>
                              {isSelected ? 'Granted' : 'No Access'}
                            </Badge>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* STEP 4: AI MODEL CONFIGURATION */}
              {wizardStep === 4 && (
                <div className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                      LLM Generation Model
                    </label>
                    <select
                      value={aiModel}
                      onChange={(e) => setAiModel(e.target.value)}
                      className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40"
                    >
                      <option value="gemini-3.5-flash">Google Gemini 3.5 Flash (Production Default — Fast &amp; Grounded)</option>
                      <option value="gemini-3.6-flash">Google Gemini 3.6 Flash (High Throughput)</option>
                      <option value="gpt-4o">OpenAI GPT-4o (Omni Reasoning)</option>
                      <option value="claude-3-5-sonnet">Anthropic Claude 3.5 Sonnet (Nuanced Analysis)</option>
                    </select>
                  </div>

                  <div className="p-4 rounded-xl bg-[#151515] border border-[#262626] space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-semibold text-[#F5F5F5]">
                        Temperature ({temperature})
                      </label>
                      <span className="text-[11px] text-[#737373]">
                        {temperature <= 0.3 ? 'Deterministic & Grounded' : temperature <= 0.7 ? 'Balanced' : 'Creative'}
                      </span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="1.0"
                      step="0.05"
                      value={temperature}
                      onChange={(e) => setTemperature(parseFloat(e.target.value))}
                      className="w-full accent-[#FF9D00] cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-[#737373] font-mono">
                      <span>0.0 (Strict Grounding)</span>
                      <span>0.5</span>
                      <span>1.0 (Creative)</span>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-[#151515] border border-[#262626] space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="text-xs font-semibold text-[#F5F5F5]">
                        Retrieval Top-K Chunks ({topK})
                      </label>
                      <span className="text-[11px] text-[#737373]">
                        Maximum relevant chunks retrieved per turn
                      </span>
                    </div>
                    <input
                      type="range"
                      min="1"
                      max="10"
                      step="1"
                      value={topK}
                      onChange={(e) => setTopK(parseInt(e.target.value))}
                      className="w-full accent-[#FF9D00] cursor-pointer"
                    />
                    <div className="flex justify-between text-[10px] text-[#737373] font-mono">
                      <span>1 Chunk</span>
                      <span>5 Chunks (Recommended)</span>
                      <span>10 Chunks</span>
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 5: TOOLS & GOVERNANCE */}
              {wizardStep === 5 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-xs font-semibold text-[#F5F5F5]">
                        Agent Tools &amp; Action Permissions
                      </h3>
                      <p className="text-[11px] text-[#737373]">
                        READ tools execute automatically; WRITE tools require human approval.
                      </p>
                    </div>
                    {allTools.length > 0 && (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={selectAllTools}
                          className="text-[11px] text-[#FF9D00] hover:text-[#FF6A00] font-semibold"
                        >
                          Select All
                        </button>
                        <span className="text-[#262626]">•</span>
                        <button
                          type="button"
                          onClick={clearAllTools}
                          className="text-[11px] text-[#737373] hover:text-[#A1A1AA]"
                        >
                          Clear
                        </button>
                      </div>
                    )}
                  </div>

                  {allTools.length === 0 ? (
                    <div className="text-center py-6 bg-[#151515] rounded-xl border border-dashed border-[#262626] text-xs text-[#737373]">
                      No tools registered. AI Employee will operate in pure Q&amp;A retrieval mode.
                    </div>
                  ) : (
                    <div className="space-y-2 max-h-60 overflow-y-auto pr-1">
                      {allTools.map((t) => {
                        const isSelected = selectedToolNames.includes(t.name);
                        const isWrite = t.permission === 'WRITE';
                        return (
                          <div
                            key={t.name}
                            onClick={() => toggleToolSelection(t.name)}
                            className={`flex items-start justify-between p-3 rounded-lg border cursor-pointer transition-editorial ${
                              isSelected
                                ? 'bg-orange-950/30 border-orange-600/50 text-white'
                                : 'bg-[#151515] border-[#262626] text-[#A1A1AA] hover:border-[#383838]'
                            }`}
                          >
                            <div className="flex items-start gap-3">
                              {isSelected ? (
                                <CheckSquare className="w-4 h-4 text-[#FF9D00] shrink-0 mt-0.5" />
                              ) : (
                                <Square className="w-4 h-4 text-[#737373] shrink-0 mt-0.5" />
                              )}
                              <div>
                                <div className="flex items-center gap-2">
                                  <p className="text-xs font-mono font-semibold text-[#FFC247]">{t.name}</p>
                                  <Badge variant={isWrite ? 'orange' : 'neutral'}>
                                    {isWrite ? 'Write (Confirmation)' : 'Read (Auto)'}
                                  </Badge>
                                </div>
                                <p className="text-[11px] text-[#737373] mt-0.5 leading-snug">
                                  {t.description}
                                </p>
                              </div>
                            </div>
                            <Badge variant={isSelected ? 'orange' : 'outline'}>
                              {isSelected ? 'Enabled' : 'Disabled'}
                            </Badge>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* STEP 6: REVIEW & LAUNCH */}
              {wizardStep === 6 && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-[#151515] border border-[#262626] space-y-3">
                    <h3 className="text-xs font-semibold text-[#F5F5F5] flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-[#FF9D00]" />
                      <span>AI Employee Configuration Summary</span>
                    </h3>

                    <div className="grid grid-cols-2 gap-3 text-xs pt-1">
                      <div>
                        <span className="text-[#737373] block text-[11px]">Name:</span>
                        <span className="text-[#F5F5F5] font-semibold">{name || '—'}</span>
                      </div>
                      <div>
                        <span className="text-[#737373] block text-[11px]">Role:</span>
                        <span className="text-[#FF9D00] font-mono">{role || '—'}</span>
                      </div>
                      <div>
                        <span className="text-[#737373] block text-[11px]">Model:</span>
                        <span className="text-[#F5F5F5] font-mono">{aiModel}</span>
                      </div>
                      <div>
                        <span className="text-[#737373] block text-[11px]">Temperature:</span>
                        <span className="text-[#F5F5F5] font-mono">{temperature}</span>
                      </div>
                      <div>
                        <span className="text-[#737373] block text-[11px]">Assigned Knowledge Bases:</span>
                        <span className="text-[#F5F5F5] font-semibold">{selectedKbIds.length} collections</span>
                      </div>
                      <div>
                        <span className="text-[#737373] block text-[11px]">Enabled Tools:</span>
                        <span className="text-[#F5F5F5] font-semibold">{selectedToolNames.length} tools</span>
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                      Deployment Status
                    </label>
                    <select
                      value={status}
                      onChange={(e) => setStatus(e.target.value as AIEmployeeStatus)}
                      className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40"
                    >
                      <option value="DRAFT">Draft (Internal Testing)</option>
                      <option value="ACTIVE">Active (Live Deployment)</option>
                      <option value="INACTIVE">Inactive (Disabled)</option>
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer Controls */}
            <div className="flex items-center justify-between pt-4 border-t border-[#262626] mt-4 shrink-0">
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={isSavingEmployee}
                onClick={() => setIsModalOpen(false)}
              >
                Cancel
              </Button>

              <div className="flex items-center gap-2">
                {wizardStep > 1 && (
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    icon={ChevronLeft}
                    onClick={() => setWizardStep((prev) => Math.max(1, prev - 1))}
                  >
                    Back
                  </Button>
                )}

                {wizardStep < 6 ? (
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    icon={ChevronRight}
                    onClick={handleNextStep}
                  >
                    Continue
                  </Button>
                ) : (
                  <Button
                    type="button"
                    variant="primary"
                    size="sm"
                    loading={isSavingEmployee}
                    onClick={() => handleSave()}
                  >
                    {editingEmployee ? 'Save Changes' : 'Create AI Employee'}
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Embed & Widget Customizer Modal */}
      {isEmbedModalOpen && activeEmbedEmployee && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-3xl p-6 shadow-card max-h-[92vh] flex flex-col">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-[#262626]">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-lg bg-[#151515] border border-[#262626] text-[#FF9D00] flex items-center justify-center">
                  <Code className="w-4 h-4" />
                </div>
                <div>
                  <h2 className="text-base font-display font-bold text-[#F5F5F5] flex items-center gap-2">
                    <span>Embed &amp; Widget Configuration</span>
                    <Badge variant="orange">{activeEmbedEmployee.name}</Badge>
                  </h2>
                  <p className="text-xs text-[#737373]">
                    Deploy your AI Employee to any website via a standalone script tag.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsEmbedModalOpen(false)}
                className="p-1.5 text-[#737373] hover:text-[#F5F5F5] hover:bg-[#151515] rounded-lg transition-editorial"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Publishing Warning Banner if Unpublished */}
            {!activeEmbedEmployee.is_published && (
              <div className="mt-4 p-3.5 rounded-xl bg-orange-950/60 border border-orange-800/50 flex items-center justify-between gap-3 text-xs text-[#FFC247]">
                <div className="flex items-center gap-2.5">
                  <AlertCircle className="w-4 h-4 text-[#FF9D00] shrink-0" />
                  <span>
                    This AI Employee is currently <strong>UNPUBLISHED</strong>. Public visitors cannot interact with the widget until published.
                  </span>
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleTogglePublish(activeEmbedEmployee)}
                >
                  Publish Now
                </Button>
              </div>
            )}

            {/* Navigation Tabs */}
            <div className="flex items-center gap-2 mt-4 border-b border-[#262626] pb-2">
              <button
                onClick={() => setActiveEmbedTab('snippet')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-editorial ${
                  activeEmbedTab === 'snippet'
                    ? 'bg-[#151515] text-[#F5F5F5] border border-[#262626] shadow-card'
                    : 'text-[#737373] hover:text-[#F5F5F5] hover:bg-[#151515]'
                }`}
              >
                <Code className="w-3.5 h-3.5" />
                <span>Embed Code</span>
              </button>
              <button
                onClick={() => setActiveEmbedTab('customizer')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-editorial ${
                  activeEmbedTab === 'customizer'
                    ? 'bg-[#151515] text-[#F5F5F5] border border-[#262626] shadow-card'
                    : 'text-[#737373] hover:text-[#F5F5F5] hover:bg-[#151515]'
                }`}
              >
                <Palette className="w-3.5 h-3.5" />
                <span>Theme &amp; Widget</span>
              </button>
              <button
                onClick={() => setActiveEmbedTab('domains')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-editorial ${
                  activeEmbedTab === 'domains'
                    ? 'bg-[#151515] text-[#F5F5F5] border border-[#262626] shadow-card'
                    : 'text-[#737373] hover:text-[#F5F5F5] hover:bg-[#151515]'
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                <span>Allowed Domains ({allowedDomainsList.length})</span>
              </button>
              <button
                onClick={() => setActiveEmbedTab('preview')}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-editorial ${
                  activeEmbedTab === 'preview'
                    ? 'bg-[#151515] text-[#F5F5F5] border border-[#262626] shadow-card'
                    : 'text-[#737373] hover:text-[#F5F5F5] hover:bg-[#151515]'
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
                    <h3 className="text-sm font-display font-semibold text-[#F5F5F5] mb-1">
                      HTML Embed Snippet
                    </h3>
                    <p className="text-xs text-[#737373]">
                      Paste this script into the <code className="text-[#FF9D00] font-mono">&lt;head&gt;</code> or bottom of the <code className="text-[#FF9D00] font-mono">&lt;body&gt;</code> tag on your website.
                    </p>
                  </div>

                  <div className="relative group">
                    <pre className="p-4 rounded-xl bg-[#050505] border border-[#262626] text-xs font-mono text-[#FFC247] overflow-x-auto whitespace-pre leading-relaxed">
                      {embedData?.embed_snippet || 'Loading embed code...'}
                    </pre>
                    <button
                      onClick={handleCopySnippet}
                      className="absolute top-3 right-3 px-3 py-1.5 rounded-lg bg-[#FF9D00] hover:bg-[#FF6A00] border border-[#FF9D00]/60 text-black text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-editorial"
                    >
                      {copiedSnippet ? (
                        <>
                          <Check className="w-3.5 h-3.5" />
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

                  <div className="p-3.5 rounded-xl bg-[#151515] border border-[#262626] text-xs text-[#737373] space-y-2">
                    <div className="font-semibold text-[#F5F5F5] flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-[#FF9D00]" />
                      <span>Security &amp; Zero-Config Runtime</span>
                    </div>
                    <ul className="list-disc list-inside space-y-1 text-[#A1A1AA]">
                      <li>Requires zero React or host runtime dependencies on the client site.</li>
                      <li>Encapsulated via <strong>Shadow DOM</strong> so host CSS cannot cause collisions.</li>
                      <li>Anonymous visitors authenticate via ephemeral Bearer headers with distributed sliding-window rate limits.</li>
                    </ul>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <span className="text-xs text-[#737373] font-mono">
                      Public ID: {embedData?.public_id || 'Generating...'}
                    </span>
                    {embedData?.public_id && (
                      <a
                        href={`/preview/${embedData.public_id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-xs text-[#FF9D00] hover:text-[#FF6A00] flex items-center gap-1 font-semibold"
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
                      <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                        Brand Name / Title
                      </label>
                      <input
                        type="text"
                        value={widgetBrandName}
                        onChange={(e) => setWidgetBrandName(e.target.value)}
                        placeholder={activeEmbedEmployee.name}
                        className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
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
                          className="flex-1 px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs font-mono text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40"
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                      Welcome Message
                    </label>
                    <input
                      type="text"
                      value={widgetWelcomeMsg}
                      onChange={(e) => setWidgetWelcomeMsg(e.target.value)}
                      placeholder="Hi! How can I help you today?"
                      className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40"
                    />
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                        Widget Position
                      </label>
                      <select
                        value={widgetPosition}
                        onChange={(e) => setWidgetPosition(e.target.value)}
                        className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40"
                      >
                        <option value="bottom-right">Bottom Right (Default)</option>
                        <option value="bottom-left">Bottom Left</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
                        Theme Mode
                      </label>
                      <select
                        value={widgetTheme}
                        onChange={(e) => setWidgetTheme(e.target.value)}
                        className="w-full px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40"
                      >
                        <option value="dark">Dark Theme</option>
                        <option value="light">Light Theme</option>
                      </select>
                    </div>
                  </div>

                  <div className="pt-2 flex justify-end">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleSaveWidgetConfig}
                      loading={isSavingWidgetConfig}
                      icon={Check}
                    >
                      Save Widget Customization
                    </Button>
                  </div>
                </div>
              )}

              {/* TAB 3: ALLOWED DOMAINS */}
              {activeEmbedTab === 'domains' && (
                <div className="space-y-4">
                  <div className="p-3.5 rounded-xl bg-[#151515] border border-[#262626] text-xs text-[#A1A1AA] leading-relaxed">
                    <strong>Integration Boundary Notice:</strong> Domain restrictions ensure unauthorized external sites cannot embed this AI employee widget. Note that domain validation is an integration control, while ephemeral sessions and rate limiting enforce visitor runtime security.
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#A1A1AA] mb-1.5">
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
                        className="flex-1 px-3.5 py-2 bg-[#151515] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] focus:outline-none focus:ring-1 focus:ring-[#FF9D00]/40"
                      />
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        onClick={handleAddDomain}
                        icon={Plus}
                      >
                        Add
                      </Button>
                    </div>
                    {domainError && (
                      <p className="mt-1.5 text-xs text-rose-400">{domainError}</p>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-semibold text-[#A1A1AA]">
                        Active Allowed Domains
                      </span>
                      <span className="text-[11px] text-[#737373] font-mono">
                        {allowedDomainsList.length === 0
                          ? 'Open mode (all origins allowed)'
                          : `${allowedDomainsList.length} domain(s) configured`}
                      </span>
                    </div>

                    {allowedDomainsList.length === 0 ? (
                      <div className="p-4 rounded-xl bg-[#0B0B0B] border border-dashed border-[#262626] text-center text-xs text-[#737373]">
                        No domains specified. The widget will accept requests from any origin (recommended for development &amp; testing).
                      </div>
                    ) : (
                      <div className="space-y-1.5 max-h-48 overflow-y-auto">
                        {allowedDomainsList.map((d) => (
                          <div
                            key={d}
                            className="flex items-center justify-between p-2.5 rounded-lg bg-[#151515] border border-[#262626] text-xs"
                          >
                            <span className="font-mono text-[#F5F5F5]">{d}</span>
                            <button
                              type="button"
                              onClick={() => handleRemoveDomain(d)}
                              className="text-[#737373] hover:text-rose-400 transition-editorial"
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
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={handleSaveWidgetConfig}
                      loading={isSavingWidgetConfig}
                      icon={Check}
                    >
                      Save Allowed Domains
                    </Button>
                  </div>
                </div>
              )}

              {/* TAB 4: LIVE PREVIEW */}
              {activeEmbedTab === 'preview' && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-xs font-semibold text-[#F5F5F5]">
                        Interactive Live Widget Preview
                      </h4>
                      <p className="text-[11px] text-[#737373]">
                        Simulating an external website with the standalone widget script loaded.
                      </p>
                    </div>
                    {embedData?.preview_url && (
                      <a
                        href={embedData.preview_url}
                        target="_blank"
                        rel="noreferrer"
                        className="px-3 py-1 bg-[#151515] hover:bg-[#1A1A1A] border border-[#262626] rounded text-xs text-[#FF9D00] hover:text-[#FF6A00] flex items-center gap-1 font-semibold transition-editorial"
                      >
                        <span>Full Page Preview</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>

                  <div className="w-full h-96 rounded-xl border border-[#262626] bg-[#050505] overflow-hidden relative">
                    {embedData?.public_id ? (
                      <iframe
                        src={`/preview/${embedData.public_id}`}
                        className="w-full h-full border-0"
                        title="Widget Preview"
                      />
                    ) : (
                      <div className="flex items-center justify-center h-full text-xs text-[#737373]">
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

