'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { AIEmployee } from '@/types';
import {
  FlaskConical,
  Bot,
  RotateCw,
  Send,
  Sliders,
  Search,
  Clock,
  ChevronRight,
  Layers,
  Terminal,
  X,
  Code,
} from 'lucide-react';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';

export default function PlaygroundPage() {
  const [employees, setEmployees] = useState<AIEmployee[]>([]);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string>('');
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSession, setActiveSession] = useState<any | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);

  // Active drawer tab: 'retrieval' | 'prompt' | 'trace'
  const [activeDrawer, setActiveDrawer] = useState<'retrieval' | 'prompt' | 'trace'>('retrieval');
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
    <div className="flex flex-col h-[calc(100vh-5.5rem)] -m-6 bg-[#050505] font-sans">
      {/* Top Header Bar */}
      <div className="h-14 border-b border-[#262626] bg-[#0B0B0B] px-6 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center text-[#FF9D00] shadow-sm">
            <FlaskConical className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-xs font-semibold font-display text-[#F5F5F5] flex items-center gap-2">
              <span>AI Employee Playground</span>
              <Badge variant="orange">Isolated Testing Console</Badge>
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs">
            <Bot className="w-4 h-4 text-[#737373]" />
            <select
              value={selectedEmployeeId}
              onChange={(e) => setSelectedEmployeeId(e.target.value)}
              className="bg-[#151515] border border-[#262626] text-[#F5F5F5] text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-[#FF9D00]"
            >
              {employees.map((e) => (
                <option key={e.id} value={e.id}>
                  {e.name} ({e.role})
                </option>
              ))}
            </select>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={() => setIsCompareOpen(true)}
            icon={Layers}
          >
            A/B Compare Configs
          </Button>

          <Button
            variant="orange"
            size="sm"
            onClick={handleCreateSession}
            icon={RotateCw}
          >
            New Session Snapshot
          </Button>
        </div>
      </div>

      {/* Main 3-Column Workspace */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT COLUMN: Config Snapshot & History */}
        <div className="w-72 border-r border-[#262626] bg-[#0B0B0B] flex flex-col shrink-0 overflow-y-auto">
          <div className="p-4 border-b border-[#262626] space-y-3">
            <div className="flex items-center justify-between text-xs font-medium text-[#A1A1AA]">
              <span className="flex items-center gap-1.5 font-display text-[#F5F5F5]">
                <Sliders className="w-3.5 h-3.5 text-[#FF9D00]" />
                Snapshot Settings
              </span>
              <Badge variant="orange">Override</Badge>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block text-[11px] font-mono text-[#737373] mb-1">Model Provider</label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full bg-[#151515] border border-[#262626] rounded-md px-2.5 py-1 text-[#F5F5F5] text-xs focus:border-[#FF9D00] focus:outline-none"
                >
                  <option value="gemini-3.6-flash">Gemini 3.6 Flash</option>
                  <option value="gemini-3.8-flash">Gemini 3.8 Flash</option>
                  <option value="gpt-4o">GPT-4o</option>
                  <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                </select>
              </div>

              <div>
                <div className="flex items-center justify-between text-[11px] font-mono text-[#737373] mb-1">
                  <span>Temperature</span>
                  <span className="text-[#FF9D00] font-bold">{temperature}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={temperature}
                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                  className="w-full accent-[#FF9D00] cursor-pointer"
                />
              </div>

              <div>
                <div className="flex items-center justify-between text-[11px] font-mono text-[#737373] mb-1">
                  <span>Retrieval Top-K</span>
                  <span className="text-[#FF9D00] font-bold">{topK}</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="15"
                  value={topK}
                  onChange={(e) => setTopK(parseInt(e.target.value))}
                  className="w-full accent-[#FF9D00] cursor-pointer"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-[#737373] mb-1">Retrieval Strategy</label>
                <select
                  value={retrievalMode}
                  onChange={(e) => setRetrievalMode(e.target.value)}
                  className="w-full bg-[#151515] border border-[#262626] rounded-md px-2.5 py-1 text-[#F5F5F5] text-xs focus:border-[#FF9D00] focus:outline-none"
                >
                  <option value="dense">Dense Vector (Qdrant Cosine)</option>
                  <option value="hybrid">Hybrid (Dense + BM25 + RRF)</option>
                  <option value="rerank">Hybrid + Cross-Encoder Rerank</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-[#737373] mb-1">System Prompt Directive</label>
                <textarea
                  rows={3}
                  value={systemPrompt}
                  onChange={(e) => setSystemPrompt(e.target.value)}
                  className="w-full bg-[#151515] border border-[#262626] rounded-md p-2 text-[#F5F5F5] text-[11px] font-mono leading-relaxed focus:border-[#FF9D00] focus:outline-none"
                />
              </div>
            </div>
          </div>

          {/* Past Sessions List */}
          <div className="p-3 flex-1 overflow-y-auto space-y-1">
            <div className="text-[10px] font-mono uppercase tracking-wider text-[#737373] px-2 mb-2">
              Debug Sessions
            </div>
            {sessions.map((s) => (
              <div
                key={s.id}
                onClick={() => loadSessionDetails(s.id)}
                className={`flex items-center justify-between p-2 rounded-lg text-xs cursor-pointer transition-colors ${
                  activeSession?.id === s.id
                    ? 'bg-[#151515] text-[#F5F5F5] font-medium border border-[#FF9D00]/40'
                    : 'text-[#A1A1AA] hover:bg-[#151515] hover:text-[#F5F5F5]'
                }`}
              >
                <span className="truncate">{s.session_name}</span>
                <button
                  onClick={(e) => handleDeleteSession(s.id, e)}
                  className="text-[#737373] hover:text-rose-400 p-1 rounded"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* CENTER COLUMN: Interactive Chat */}
        <div className="flex-1 flex flex-col bg-[#050505]">
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-[#737373] space-y-3">
                <div className="w-12 h-12 rounded-xl bg-[#101010] border border-[#262626] flex items-center justify-center text-[#FF9D00]">
                  <Terminal className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-semibold font-display text-[#F5F5F5]">Playground Ready</h3>
                <p className="text-xs text-[#A1A1AA] max-w-sm leading-relaxed">
                  Send a query to execute the live AI Employee pipeline and inspect retrieval chunks, prompt construction, and execution traces in real time.
                </p>
              </div>
            ) : (
              messages.map((m) => {
                const isUser = m.role === 'user';
                return (
                  <div
                    key={m.id}
                    onClick={() => !isUser && setSelectedMessage(m)}
                    className={`flex flex-col ${
                      isUser ? 'items-end' : 'items-start cursor-pointer group'
                    }`}
                  >
                    <div
                      className={`max-w-2xl p-4 rounded-xl text-xs leading-relaxed ${
                        isUser
                          ? 'bg-[#FF9D00] text-black font-medium'
                          : `bg-[#101010] border ${
                              selectedMessage?.id === m.id
                                ? 'border-[#FF9D00]'
                                : 'border-[#262626] group-hover:border-[#333333]'
                            } text-[#F5F5F5]`
                      }`}
                    >
                      <div className="whitespace-pre-wrap">{m.content}</div>

                      {!isUser && (
                        <div className="mt-3 pt-2.5 border-t border-[#262626] flex items-center justify-between text-[11px] text-[#737373] font-mono">
                          <span className="flex items-center gap-1.5 text-[#FF9D00]">
                            <Clock className="w-3 h-3" />
                            {m.execution_time_ms ? `${m.execution_time_ms.toFixed(0)}ms` : 'Recorded'}
                          </span>
                          <span className="text-[#A1A1AA]">
                            {m.tokens_used ? `${m.tokens_used.total_tokens || 0} tokens` : 'Token ledger'}
                          </span>
                          <span className="text-[#FF9D00] flex items-center gap-1 font-sans">
                            <span>Inspect context</span>
                            <ChevronRight className="w-3 h-3" />
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
            {sending && (
              <div className="flex items-center gap-2 text-xs text-[#FF9D00] font-mono p-3 bg-[#101010] border border-[#262626] rounded-xl max-w-xs">
                <div className="w-2 h-2 rounded-full bg-[#FF9D00] animate-pulse" />
                <span>Executing RAG retrieval & inference...</span>
              </div>
            )}
          </div>

          <div className="p-4 bg-[#0B0B0B] border-t border-[#262626]">
            <form onSubmit={handleSendMessage} className="flex gap-2">
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder="Ask a question or test edge cases..."
                className="flex-1 bg-[#101010] border border-[#262626] rounded-lg px-4 py-2.5 text-xs text-[#F5F5F5] placeholder-[#737373] focus:outline-none focus:border-[#FF9D00]"
              />
              <Button variant="orange" size="md" type="submit" disabled={sending || !inputQuery.trim()} icon={Send}>
                Send
              </Button>
            </form>
          </div>
        </div>

        {/* RIGHT COLUMN: Inspector Drawer */}
        <div className="w-96 border-l border-[#262626] bg-[#0B0B0B] flex flex-col shrink-0 overflow-hidden">
          {/* Drawer Tab Headers */}
          <div className="h-12 border-b border-[#262626] px-3 flex items-center gap-1 shrink-0 bg-[#0B0B0B]">
            <button
              onClick={() => setActiveDrawer('retrieval')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors ${
                activeDrawer === 'retrieval'
                  ? 'bg-[#151515] text-[#FF9D00] border border-[#262626]'
                  : 'text-[#737373] hover:text-[#F5F5F5]'
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              <span>Retrieval</span>
            </button>
            <button
              onClick={() => setActiveDrawer('prompt')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors ${
                activeDrawer === 'prompt'
                  ? 'bg-[#151515] text-[#FF9D00] border border-[#262626]'
                  : 'text-[#737373] hover:text-[#F5F5F5]'
              }`}
            >
              <Code className="w-3.5 h-3.5" />
              <span>Prompt</span>
            </button>
            <button
              onClick={() => setActiveDrawer('trace')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium flex items-center gap-1.5 transition-colors ${
                activeDrawer === 'trace'
                  ? 'bg-[#151515] text-[#FF9D00] border border-[#262626]'
                  : 'text-[#737373] hover:text-[#F5F5F5]'
              }`}
            >
              <Clock className="w-3.5 h-3.5" />
              <span>Trace</span>
            </button>
          </div>

          {/* Drawer Body Content */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {!selectedMessage ? (
              <div className="h-full flex items-center justify-center text-center text-xs text-[#737373] p-4 font-mono">
                Select an assistant message to inspect retrieval context and telemetry.
              </div>
            ) : (
              <>
                {/* TAB 1: RETRIEVAL CONTEXT */}
                {activeDrawer === 'retrieval' && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold font-display text-[#F5F5F5]">Retrieved Chunks</span>
                      <Badge variant="orange">
                        {selectedMessage.retrieval_debug?.retrieved_chunks?.length || 0} Chunks
                      </Badge>
                    </div>

                    {selectedMessage.retrieval_debug?.retrieved_chunks?.map((c: any, i: number) => (
                      <div key={i} className="p-3 bg-[#101010] border border-[#262626] rounded-lg text-xs space-y-1.5">
                        <div className="flex items-center justify-between text-[10px] text-[#737373] font-mono">
                          <span className="text-[#FF9D00] font-bold truncate max-w-[140px]">
                            {c.document_title || `Doc #${c.document_id?.slice(0, 6)}`}
                          </span>
                          <span>Score: {c.score ? c.score.toFixed(3) : 'N/A'}</span>
                        </div>
                        <p className="text-[#D4D4D8] text-[11px] leading-relaxed font-mono whitespace-pre-wrap bg-[#050505] p-2.5 rounded border border-[#262626]">
                          {c.content || c.snippet}
                        </p>
                      </div>
                    ))}
                  </div>
                )}

                {/* TAB 2: PROMPT ASSEMBLY */}
                {activeDrawer === 'prompt' && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-semibold font-display text-[#F5F5F5]">Assembled Prompt</span>
                      <Badge variant="neutral">PII Redacted</Badge>
                    </div>
                    <pre className="p-3 bg-[#050505] border border-[#262626] rounded-lg text-[11px] font-mono text-[#D4D4D8] whitespace-pre-wrap leading-relaxed">
                      {selectedMessage.prompt_debug?.assembled_prompt ||
                        selectedMessage.prompt_debug?.system_prompt ||
                        'Prompt assembly context generated by agent brain.'}
                    </pre>
                  </div>
                )}

                {/* TAB 3: TRACE & LATENCY */}
                {activeDrawer === 'trace' && (
                  <div className="space-y-3 text-xs">
                    <div className="p-3.5 bg-[#101010] border border-[#262626] rounded-lg space-y-2.5">
                      <div className="flex justify-between font-mono text-[11px]">
                        <span className="text-[#737373]">Total Latency:</span>
                        <span className="text-[#F5F5F5] font-bold">{selectedMessage.execution_time_ms || 0} ms</span>
                      </div>
                      <div className="flex justify-between font-mono text-[11px]">
                        <span className="text-[#737373]">Model:</span>
                        <span className="text-[#FF9D00]">{model}</span>
                      </div>
                      <div className="flex justify-between font-mono text-[11px]">
                        <span className="text-[#737373]">Tokens:</span>
                        <span className="text-[#A1A1AA]">
                          {selectedMessage.tokens_used?.total_tokens || 'Recorded in ledger'}
                        </span>
                      </div>
                      <div className="flex justify-between font-mono text-[11px]">
                        <span className="text-[#737373]">Cost:</span>
                        <span className="text-[#FF9D00]">
                          {selectedMessage.cost ? `$${selectedMessage.cost.toFixed(4)}` : '$0.0000'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* A/B COMPARISON MODAL */}
      {isCompareOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-4xl p-6 shadow-2xl max-h-[90vh] flex flex-col space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262626]">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-[#FF9D00]" />
                <h3 className="text-sm font-semibold font-display text-[#F5F5F5]">Compare AI Employee Configurations</h3>
              </div>
              <button
                onClick={() => setIsCompareOpen(false)}
                className="text-[#737373] hover:text-[#F5F5F5] p-1 rounded hover:bg-[#1A1A1A]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex gap-2">
              <input
                type="text"
                value={compareQuery}
                onChange={(e) => setCompareQuery(e.target.value)}
                placeholder="Enter test prompt to run against both configurations side-by-side..."
                className="flex-1 bg-[#050505] border border-[#262626] rounded-lg px-3 py-2 text-xs text-[#F5F5F5] placeholder-[#737373] focus:outline-none focus:border-[#FF9D00]"
              />
              <Button
                variant="orange"
                size="sm"
                onClick={handleRunComparison}
                disabled={comparing || !compareQuery.trim()}
                loading={comparing}
              >
                Run Side-by-Side
              </Button>
            </div>

            {compareResults && (
              <div className="grid grid-cols-2 gap-4 flex-1 overflow-y-auto pt-2">
                <div className="p-4 bg-[#0B0B0B] border border-[#262626] rounded-lg space-y-2">
                  <div className="flex items-center justify-between font-bold text-xs text-[#FF9D00]">
                    <span>Config A (Baseline)</span>
                    <Badge variant="orange">Temp 0.2</Badge>
                  </div>
                  <div className="text-xs text-[#D4D4D8] leading-relaxed font-mono whitespace-pre-wrap p-3 bg-[#050505] border border-[#262626] rounded">
                    {compareResults.results?.config_a?.response || 'No response recorded'}
                  </div>
                </div>

                <div className="p-4 bg-[#0B0B0B] border border-[#262626] rounded-lg space-y-2">
                  <div className="flex items-center justify-between font-bold text-xs text-[#FFC247]">
                    <span>Config B (Structured Directives)</span>
                    <Badge variant="sand">Temp 0.7</Badge>
                  </div>
                  <div className="text-xs text-[#D4D4D8] leading-relaxed font-mono whitespace-pre-wrap p-3 bg-[#050505] border border-[#262626] rounded">
                    {compareResults.results?.config_b?.response || 'No response recorded'}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
