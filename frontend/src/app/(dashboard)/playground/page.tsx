'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { AIEmployee } from '@/types';
import {
  FlaskConical,
  Bot,
  Play,
  RotateCw,
  Send,
  Sliders,
  Search,
  FileText,
  Clock,
  Coins,
  ShieldCheck,
  ChevronRight,
  Layers,
  Sparkles,
  Info,
  CheckCircle2,
  Trash2,
  X,
  Code,
  ArrowRight,
} from 'lucide-react';

export default function PlaygroundPage() {
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('');
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<any | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);

  // Active drawer tab: 'retrieval' | 'prompt' | 'trace' | null
  const [activeDrawer, setActiveDrawer] = useState<'retrieval' | 'prompt' | 'trace' | null>('retrieval');
  const [selectedMessage, setSelectedMessage] = useState<any | null>(null);

  // Configuration snapshot editor state
  const [systemPrompt, setSystemPrompt] = useState('');
  const [personality, setPersonality] = useState('');
  const [model, setModel] = useState('gemini-3.6-flash');
  const [temperature, setTemperature] = useState(0.2);
  const [topK, setTopK] = useState(5);
  const [retrievalMode, setRetrievalMode] = useState('dense');

  // Compare Modal
  const [isCompareOpen, setIsCompareOpen] = useState(false);
  const [compareQuery, setCompareQuery] = useState('');
  const [compareResults, setCompareResults] = useState<any | null>(null);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    loadEmployees();
  }, []);

  useEffect(() => {
    if (selectedEmployeeId) {
      loadSessions(selectedEmployeeId);
      const emp = employees.find((e) => e.id === selectedEmployeeId);
      if (emp) {
        setSystemPrompt(emp.system_prompt || '');
        setPersonality(emp.personality || '');
      }
    }
  }, [selectedEmployeeId]);

  const loadEmployees = async () => {
    try {
      const data = await api.getAIEmployees();
      setEmployees(data);
      if (data.length > 0 && !selectedEmployeeId) {
        setSelectedEmployeeId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load AI employees', err);
    }
  };

  const loadSessions = async (empId: string) => {
    setLoading(true);
    try {
      const data = await api.listPlaygroundSessions(empId);
      setSessions(data);
      if (data.length > 0) {
        loadSessionDetails(data[0].id);
      } else {
        setActiveSession(null);
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to load playground sessions', err);
    } finally {
      setLoading(false);
    }
  };

  const loadSessionDetails = async (sessionId: string) => {
    try {
      const res = await api.getPlaygroundSession(sessionId);
      setActiveSession(res.session);
      setMessages(res.messages);
      if (res.session.config_snapshot) {
        const snap = res.session.config_snapshot;
        setSystemPrompt(snap.system_prompt || '');
        setPersonality(snap.personality || '');
        setModel(snap.model || 'gemini-3.6-flash');
        setTemperature(snap.temperature || 0.2);
        setTopK(snap.top_k || 5);
        setRetrievalMode(snap.retrieval_mode || 'dense');
      }
      if (res.messages.length > 0) {
        const lastAssist = [...res.messages].reverse().find((m) => m.role === 'assistant');
        setSelectedMessage(lastAssist || null);
      }
    } catch (err) {
      console.error('Failed to load session details', err);
    }
  };

  const handleCreateSession = async () => {
    if (!selectedEmployeeId) return;
    try {
      const newSession = await api.createPlaygroundSession({
        ai_employee_id: selectedEmployeeId,
        session_name: `Snapshot: ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`,
        config_overrides: {
          system_prompt: systemPrompt,
          personality,
          model,
          temperature,
          top_k: topK,
          retrieval_mode: retrievalMode,
        },
      });
      setSessions([newSession, ...sessions]);
      setActiveSession(newSession);
      setMessages([]);
    } catch (err) {
      console.error('Failed to create session', err);
    }
  };

  const handleDeleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.deletePlaygroundSession(sessionId);
      const filtered = sessions.filter((s) => s.id !== sessionId);
      setSessions(filtered);
      if (activeSession?.id === sessionId) {
        if (filtered.length > 0) {
          loadSessionDetails(filtered[0].id);
        } else {
          setActiveSession(null);
          setMessages([]);
        }
      }
    } catch (err) {
      console.error('Failed to delete session', err);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputQuery.trim() || sending) return;

    if (!activeSession) {
      await handleCreateSession();
    }

    const currentSessionId = activeSession?.id;
    if (!currentSessionId) return;

    const query = inputQuery.trim();
    setInputQuery('');
    setSending(true);

    try {
      const res = await api.sendPlaygroundMessage(currentSessionId, query);
      setMessages((prev) => [...prev, res.user_message, res.assistant_message]);
      setSelectedMessage(res.assistant_message);
    } catch (err: any) {
      console.error('Failed to send playground message', err);
      alert(err.message || 'Error processing request');
    } finally {
      setSending(false);
    }
  };

  const handleRunComparison = async () => {
    if (!compareQuery.trim() || !selectedEmployeeId || comparing) return;
    setComparing(true);
    try {
      const res = await api.compareConfigurations({
        ai_employee_id: selectedEmployeeId,
        test_queries: [compareQuery.trim()],
        config_a: {
          system_prompt: systemPrompt,
          personality,
          model,
          temperature: 0.2,
        },
        config_b: {
          system_prompt: `${systemPrompt}\n\nBe extremely structured and comprehensive with bullet points.`,
          personality,
          model,
          temperature: 0.7,
        },
      });
      setCompareResults(res);
    } catch (err) {
      console.error('Comparison failed', err);
    } finally {
      setComparing(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] overflow-hidden">
      {/* Top Header Bar */}
      <div className="h-14 border-b border-slate-800 bg-slate-900/60 backdrop-blur px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
            <FlaskConical className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white flex items-center gap-2">
              AI Employee Playground
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                Phase 12
              </span>
            </h1>
            <p className="text-[11px] text-slate-400">
              Isolated testing, retrieval debugging, and safe prompt configuration
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Employee Selector */}
          <div className="flex items-center gap-2 text-xs">
            <Bot className="w-4 h-4 text-slate-400" />
            <select
              value={selectedEmployeeId}
              onChange={(e) => setSelectedEmployeeId(e.target.value)}
              className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-amber-500"
            >
              {employees.map((emp) => (
                <option key={emp.id} value={emp.id}>
                  {emp.name} ({emp.role})
                </option>
              ))}
            </select>
          </div>

          <button
            onClick={() => setIsCompareOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            <Layers className="w-3.5 h-3.5 text-indigo-400" />
            Compare Configs
          </button>

          <button
            onClick={handleCreateSession}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-medium shadow-sm transition"
          >
            <Sparkles className="w-3.5 h-3.5" />
            New Test Session
          </button>
        </div>
      </div>

      {/* Main 3-Column Layout: Sessions/Config Sidebar | Chat | Inspector Drawer */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left Column: Sessions & Snapshot Config */}
        <div className="w-80 border-r border-slate-800 bg-slate-900/40 flex flex-col shrink-0 overflow-y-auto">
          {/* Sessions List */}
          <div className="p-3 border-b border-slate-800">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2 flex justify-between items-center">
              <span>Test Sessions</span>
              <span className="text-[10px] text-slate-400">({sessions.length})</span>
            </div>
            <div className="space-y-1 max-h-36 overflow-y-auto">
              {sessions.map((s) => (
                <div
                  key={s.id}
                  onClick={() => loadSessionDetails(s.id)}
                  className={`p-2 rounded-lg text-xs cursor-pointer flex items-center justify-between group transition ${
                    activeSession?.id === s.id
                      ? 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                      : 'text-slate-300 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="truncate pr-2">
                    <div className="font-medium truncate">{s.session_name}</div>
                    <div className="text-[10px] text-slate-400">
                      {new Date(s.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(s.id, e)}
                    className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-rose-400 transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
              {sessions.length === 0 && (
                <div className="text-xs text-slate-400 py-3 text-center">No test sessions yet</div>
              )}
            </div>
          </div>

          {/* Config Snapshot Editor */}
          <div className="p-3 flex-1 space-y-3 overflow-y-auto text-xs">
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
              <Sliders className="w-3.5 h-3.5 text-amber-400" />
              <span>Snapshot Config</span>
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 mb-1">System Instructions</label>
              <textarea
                rows={4}
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500 resize-none font-mono"
                placeholder="Custom persona and behavioral rules..."
              />
            </div>

            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Personality / Tone</label>
              <input
                type="text"
                value={personality}
                onChange={(e) => setPersonality(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-amber-500"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Model</label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-1.5 text-xs text-slate-200 focus:outline-none"
                >
                  <option value="gemini-3.6-flash">gemini-3.6-flash</option>
                  <option value="gemini-2.5-flash-lite">gemini-2.5-flash-lite</option>
                  <option value="gpt-4o-mini">gpt-4o-mini</option>
                  <option value="mock-model">mock-model (offline)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Temperature ({temperature})</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full mt-2 accent-amber-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Retrieval Mode</label>
                <select
                  value={retrievalMode}
                  onChange={(e) => setRetrievalMode(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-1.5 text-xs text-slate-200 focus:outline-none"
                >
                  <option value="dense">Dense (Vector)</option>
                  <option value="sparse">Sparse (BM25)</option>
                  <option value="hybrid">Hybrid (RRF)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] text-slate-400 mb-1">Top-K ({topK})</label>
                <input
                  type="number"
                  min="1"
                  max="20"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value) || 5)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-2.5 py-1 text-xs text-slate-200 focus:outline-none"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Middle Column: Chat Window */}
        <div className="flex-1 flex flex-col bg-slate-950/60 overflow-hidden">
          {/* Chat Messages */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4">
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 text-xs">
                <FlaskConical className="w-10 h-10 text-slate-600 mb-2" />
                <p className="font-medium text-slate-400">Playground session is ready</p>
                <p className="text-[11px] text-slate-400 mt-1 max-w-sm text-center">
                  Send a test question to verify grounded RAG retrieval, prompt assembly, and token consumption without modifying production data.
                </p>
              </div>
            )}

            {messages.map((m, idx) => {
              const isUser = m.role === 'user';
              const isSelected = selectedMessage?.id === m.id;
              return (
                <div
                  key={idx}
                  onClick={() => !isUser && setSelectedMessage(m)}
                  className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} cursor-pointer`}
                >
                  <div
                    className={`max-w-[80%] rounded-xl px-4 py-2.5 text-xs transition ${
                      isUser
                        ? 'bg-amber-600 text-white rounded-br-sm'
                        : isSelected
                        ? 'bg-slate-800 text-slate-200 border border-amber-500/40 rounded-bl-sm shadow-md'
                        : 'bg-slate-900 text-slate-200 border border-slate-800 rounded-bl-sm hover:border-slate-700'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{m.content}</div>

                    {!isUser && (
                      <div className="mt-2 pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] text-slate-400">
                        <div className="flex items-center gap-3">
                          {m.metrics?.total_latency_ms && (
                            <span className="flex items-center gap-1">
                              <Clock className="w-3 h-3 text-slate-400" />
                              {m.metrics.total_latency_ms}ms
                            </span>
                          )}
                          {m.metrics?.total_tokens && (
                            <span className="flex items-center gap-1">
                              <Coins className="w-3 h-3 text-amber-400/80" />
                              {m.metrics.total_tokens} tokens
                            </span>
                          )}
                        </div>
                        {m.trace_id && (
                          <span className="font-mono text-cyan-400/80">
                            trace: {m.trace_id.slice(0, 8)}...
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Chat Input Bar */}
          <form onSubmit={handleSendMessage} className="p-3 border-t border-slate-800 bg-slate-900/40 flex gap-2">
            <input
              type="text"
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask a question to test retrieval and prompt behavior..."
              disabled={sending}
              className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-amber-500"
            />
            <button
              type="submit"
              disabled={sending || !inputQuery.trim()}
              className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:opacity-50 text-white text-xs font-medium flex items-center gap-1.5 transition"
            >
              {sending ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
              Send
            </button>
          </form>
        </div>

        {/* Right Column: Retrieval & Prompt Inspector Drawer */}
        <div className="w-96 border-l border-slate-800 bg-slate-900/60 flex flex-col shrink-0 overflow-hidden">
          {/* Drawer Navigation Tabs */}
          <div className="flex border-b border-slate-800 text-xs">
            <button
              onClick={() => setActiveDrawer('retrieval')}
              className={`flex-1 py-2.5 font-medium flex items-center justify-center gap-1.5 border-b-2 transition ${
                activeDrawer === 'retrieval'
                  ? 'border-amber-500 text-amber-400 bg-slate-800/40'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              Retrieval Inspector
            </button>
            <button
              onClick={() => setActiveDrawer('prompt')}
              className={`flex-1 py-2.5 font-medium flex items-center justify-center gap-1.5 border-b-2 transition ${
                activeDrawer === 'prompt'
                  ? 'border-amber-500 text-amber-400 bg-slate-800/40'
                  : 'border-transparent text-slate-400 hover:text-slate-200'
              }`}
            >
              <Code className="w-3.5 h-3.5" />
              Prompt Inspector
            </button>
          </div>

          {/* Drawer Content */}
          <div className="flex-1 p-3 overflow-y-auto text-xs space-y-3">
            {!selectedMessage ? (
              <div className="h-full flex flex-col items-center justify-center text-slate-400 text-xs">
                <Info className="w-6 h-6 text-slate-600 mb-1" />
                <p>Select an assistant reply to inspect its retrieval chunks and prompt structure</p>
              </div>
            ) : activeDrawer === 'retrieval' ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-slate-400">
                  <span className="font-semibold text-slate-300">Retrieved Chunks</span>
                  <span className="text-[11px]">
                    {selectedMessage.retrieval_debug?.length || 0} chunks returned
                  </span>
                </div>

                {selectedMessage.retrieval_debug?.map((chunk: any, i: number) => (
                  <div key={i} className="p-2.5 rounded-lg bg-slate-800/80 border border-slate-700/60 space-y-1.5">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-amber-400 font-semibold text-[11px]">
                        Rank #{chunk.rank}
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-700 text-slate-300 font-mono">
                        Score: {chunk.score}
                      </span>
                    </div>
                    <div className="text-[11px] font-medium text-slate-200 truncate">
                      {chunk.document_name} {chunk.page_number && `(p. ${chunk.page_number})`}
                    </div>
                    <p className="text-[11px] text-slate-400 italic line-clamp-3 bg-slate-900/60 p-1.5 rounded">
                      &quot;{chunk.preview}&quot;
                    </p>
                  </div>
                ))}

                {(!selectedMessage.retrieval_debug || selectedMessage.retrieval_debug.length === 0) && (
                  <div className="text-xs text-slate-400 text-center py-4">No chunks retrieved for this turn.</div>
                )}
              </div>
            ) : (
              <div className="space-y-3">
                <div className="text-slate-300 font-semibold">Prompt Structure</div>
                {selectedMessage.prompt_debug ? (
                  <div className="space-y-2">
                    <div className="p-2 rounded bg-slate-800/60 border border-slate-700">
                      <div className="text-[10px] uppercase text-slate-400 font-mono mb-1">System Instructions</div>
                      <div className="text-[11px] text-slate-200 whitespace-pre-wrap font-mono">
                        {selectedMessage.prompt_debug.system_prompt || '(None)'}
                      </div>
                    </div>

                    <div className="p-2 rounded bg-slate-800/60 border border-slate-700">
                      <div className="text-[10px] uppercase text-slate-400 font-mono mb-1">Persona & Tone</div>
                      <div className="text-[11px] text-slate-200 font-mono">
                        {selectedMessage.prompt_debug.personality || '(None)'}
                      </div>
                    </div>

                    <div className="p-2 rounded bg-slate-800/60 border border-slate-700">
                      <div className="text-[10px] uppercase text-slate-400 font-mono mb-1">Retrieved Context Preview</div>
                      <div className="text-[11px] text-slate-300 font-mono line-clamp-4">
                        {selectedMessage.prompt_debug.retrieved_context_preview || '(No context retrieved)'}
                      </div>
                    </div>

                    <div className="flex gap-2">
                      <div className="flex-1 p-2 rounded bg-slate-800/60 border border-slate-700 text-center">
                        <div className="text-[10px] text-slate-400">Model</div>
                        <div className="text-[11px] font-mono text-slate-200">{selectedMessage.prompt_debug.model}</div>
                      </div>
                      <div className="flex-1 p-2 rounded bg-slate-800/60 border border-slate-700 text-center">
                        <div className="text-[10px] text-slate-400">Temperature</div>
                        <div className="text-[11px] font-mono text-slate-200">{selectedMessage.prompt_debug.temperature}</div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-xs text-slate-400 text-center py-4">No prompt debug data available.</div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Compare Modal */}
      {isCompareOpen && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-3xl w-full p-5 space-y-4 shadow-xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-400" />
                Side-by-Side Configuration Comparison
              </h2>
              <button onClick={() => setIsCompareOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs text-slate-300 mb-1">Test Question</label>
                <input
                  type="text"
                  value={compareQuery}
                  onChange={(e) => setCompareQuery(e.target.value)}
                  placeholder="Enter a customer query to test against both configurations..."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none"
                />
              </div>

              <div className="flex justify-end">
                <button
                  onClick={handleRunComparison}
                  disabled={comparing || !compareQuery.trim()}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium flex items-center gap-1.5 transition"
                >
                  {comparing ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                  Execute Comparison
                </button>
              </div>

              {compareResults && (
                <div className="grid grid-cols-2 gap-3 pt-3 border-t border-slate-800">
                  <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700 space-y-2">
                    <div className="font-semibold text-xs text-amber-400">Configuration A (Current)</div>
                    <div className="text-[11px] text-slate-300">
                      {compareResults.comparisons[0]?.config_a?.answer}
                    </div>
                    <div className="text-[10px] text-slate-400 pt-2 border-t border-slate-700 flex justify-between">
                      <span>Latency: {compareResults.comparisons[0]?.config_a?.latency_ms}ms</span>
                      <span>Tokens: {compareResults.comparisons[0]?.config_a?.total_tokens}</span>
                    </div>
                  </div>

                  <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700 space-y-2">
                    <div className="font-semibold text-xs text-indigo-400">Configuration B (Alternative)</div>
                    <div className="text-[11px] text-slate-300">
                      {compareResults.comparisons[0]?.config_b?.answer}
                    </div>
                    <div className="text-[10px] text-slate-400 pt-2 border-t border-slate-700 flex justify-between">
                      <span>Latency: {compareResults.comparisons[0]?.config_b?.latency_ms}ms</span>
                      <span>Tokens: {compareResults.comparisons[0]?.config_b?.total_tokens}</span>
                    </div>
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
