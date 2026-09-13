'use client';

import React, { useEffect, useState, useRef } from 'react';
import { api } from '@/lib/api';
import { KnowledgeBase, DocumentItem, DocumentChunkItem } from '@/types';
import {
  BookOpen,
  Plus,
  UploadCloud,
  FileText,
  Trash2,
  AlertCircle,
  CheckCircle2,
  Loader2,
  ArrowLeft,
  X,
  FileCode,
  FileSpreadsheet,
  Layers,
  Database,
  Info,
} from 'lucide-react';

export default function KnowledgeBasePage() {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [docsLoading, setDocsLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // New KB Modal
  const [isKbModalOpen, setIsKbModalOpen] = useState(false);
  const [newKbName, setNewKbName] = useState('');
  const [newKbDesc, setNewKbDesc] = useState('');

  // Chunks Inspector Modal
  const [inspectingDoc, setInspectingDoc] = useState<DocumentItem | null>(null);
  const [chunks, setChunks] = useState<DocumentChunkItem[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadKnowledgeBases = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getKnowledgeBases();
      setKnowledgeBases(data);
      if (data.length > 0 && !selectedKb) {
        setSelectedKb(data[0]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load knowledge bases');
    } finally {
      setLoading(false);
    }
  };

  const loadDocuments = async (kbId: string) => {
    setDocsLoading(true);
    try {
      const data = await api.getDocuments(kbId);
      setDocuments(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load documents');
    } finally {
      setDocsLoading(false);
    }
  };

  useEffect(() => {
    loadKnowledgeBases();
  }, []);

  useEffect(() => {
    if (selectedKb) {
      loadDocuments(selectedKb.id);
    }
  }, [selectedKb]);

  const handleCreateKb = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKbName.trim()) return;
    setError(null);
    try {
      const created = await api.createKnowledgeBase({
        name: newKbName.trim(),
        description: newKbDesc.trim() || undefined,
      });
      setSuccess(`Created Knowledge Base "${created.name}"`);
      setIsKbModalOpen(false);
      setNewKbName('');
      setNewKbDesc('');
      await loadKnowledgeBases();
      setSelectedKb(created);
    } catch (err: any) {
      setError(err.message || 'Failed to create knowledge base');
    }
  };

  const handleDeleteKb = async (kb: KnowledgeBase) => {
    if (!confirm(`Are you sure you want to delete "${kb.name}" and all its documents and vectors?`)) return;
    try {
      await api.deleteKnowledgeBase(kb.id);
      setSuccess(`Deleted Knowledge Base "${kb.name}"`);
      setSelectedKb(null);
      await loadKnowledgeBases();
    } catch (err: any) {
      setError(err.message || 'Failed to delete knowledge base');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedKb) return;

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const doc = await api.uploadDocument(selectedKb.id, file);
      setSuccess(`Document "${doc.original_filename}" uploaded and processed successfully`);
      await loadDocuments(selectedKb.id);
    } catch (err: any) {
      setError(err.message || 'Upload failed');
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteDoc = async (doc: DocumentItem) => {
    if (!confirm(`Delete "${doc.original_filename}"? This will remove its text chunks and vector embeddings.`)) return;
    try {
      await api.deleteDocument(doc.id);
      setSuccess(`Deleted document "${doc.original_filename}"`);
      if (selectedKb) {
        await loadDocuments(selectedKb.id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete document');
    }
  };

  const handleInspectChunks = async (doc: DocumentItem) => {
    setInspectingDoc(doc);
    setChunksLoading(true);
    try {
      const chunkData = await api.getDocumentChunks(doc.id);
      setChunks(chunkData);
    } catch (err: any) {
      setError(err.message || 'Failed to load chunks');
    } finally {
      setChunksLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const getFileIcon = (fileType: string) => {
    const ft = fileType.toLowerCase();
    if (ft === 'pdf') return <FileText className="w-5 h-5 text-rose-400" />;
    if (ft === 'docx') return <FileText className="w-5 h-5 text-blue-400" />;
    if (ft === 'md') return <FileCode className="w-5 h-5 text-emerald-400" />;
    if (ft === 'csv') return <FileSpreadsheet className="w-5 h-5 text-amber-400" />;
    return <FileText className="w-5 h-5 text-slate-400" />;
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-mono mb-2">
            <Database className="w-3.5 h-3.5" />
            <span>Phase 1: Knowledge Ingestion &amp; Qdrant Vectors</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-100">Knowledge Base Management</h1>
          <p className="text-sm text-slate-400 mt-1">
            Upload company policies, manuals, and datasets to generate indexed semantic embeddings.
          </p>
        </div>

        <button
          onClick={() => setIsKbModalOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg shadow-sm transition-all"
        >
          <Plus className="w-4 h-4" />
          New Knowledge Base
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

      {/* Main Content Layout */}
      {loading ? (
        <div className="py-16 text-center text-sm text-slate-500">Loading knowledge infrastructure...</div>
      ) : knowledgeBases.length === 0 ? (
        <div className="py-16 text-center border border-dashed border-slate-800 rounded-xl bg-slate-900/40">
          <BookOpen className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h3 className="text-base font-semibold text-slate-200">No Knowledge Bases Found</h3>
          <p className="text-sm text-slate-400 mt-1 max-w-md mx-auto">
            Create your first company knowledge base to begin uploading documentation, PDFs, and data.
          </p>
          <button
            onClick={() => setIsKbModalOpen(true)}
            className="mt-5 inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg"
          >
            <Plus className="w-4 h-4" /> Create Knowledge Base
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Knowledge Bases Sidebar List */}
          <div className="lg:col-span-1 space-y-2">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Knowledge Bases ({knowledgeBases.length})
            </h2>
            {knowledgeBases.map((kb) => (
              <button
                key={kb.id}
                onClick={() => setSelectedKb(kb)}
                className={`w-full text-left p-3 rounded-lg border transition-all flex items-start justify-between ${
                  selectedKb?.id === kb.id
                    ? 'bg-indigo-600/15 border-indigo-500/40 text-white'
                    : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <div className="truncate">
                  <div className="font-semibold text-sm truncate">{kb.name}</div>
                  {kb.description && (
                    <div className="text-xs text-slate-400 truncate mt-0.5">{kb.description}</div>
                  )}
                </div>
              </button>
            ))}
          </div>

          {/* Selected Knowledge Base & Documents Panel */}
          <div className="lg:col-span-3 space-y-5">
            {selectedKb ? (
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-6">
                {/* KB Header */}
                <div className="flex items-start justify-between pb-4 border-b border-slate-800">
                  <div>
                    <h2 className="text-lg font-bold text-white flex items-center gap-2">
                      <BookOpen className="w-5 h-5 text-indigo-400" />
                      {selectedKb.name}
                    </h2>
                    {selectedKb.description && (
                      <p className="text-xs text-slate-400 mt-1">{selectedKb.description}</p>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteKb(selectedKb)}
                    className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded transition-colors"
                    title="Delete Knowledge Base"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                {/* Upload Box */}
                <div className="p-6 border-2 border-dashed border-slate-700/80 rounded-xl bg-slate-950/40 text-center">
                  <UploadCloud className="w-10 h-10 text-indigo-400 mx-auto mb-2" />
                  <h3 className="text-sm font-semibold text-slate-200">
                    Upload documents to index into vector search
                  </h3>
                  <p className="text-xs text-slate-400 mt-1">
                    Supported formats: PDF, DOCX, Markdown, TXT, CSV (up to 25MB)
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.docx,.md,.txt,.csv,text/markdown,text/plain,text/csv,application/pdf"
                    onChange={handleFileUpload}
                    className="hidden"
                    id="doc-upload"
                    disabled={uploading}
                  />
                  <label
                    htmlFor="doc-upload"
                    className={`mt-4 inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg cursor-pointer transition-all ${
                      uploading ? 'opacity-50 pointer-events-none' : ''
                    }`}
                  >
                    {uploading ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Extracting &amp; Vectorizing Chunks...
                      </>
                    ) : (
                      <>
                        <Plus className="w-3.5 h-3.5" /> Select File to Ingest
                      </>
                    )}
                  </label>
                </div>

                {/* Document List */}
                <div>
                  <h3 className="text-sm font-semibold text-slate-200 mb-3">
                    Ingested Documents ({documents.length})
                  </h3>

                  {docsLoading ? (
                    <div className="py-8 text-center text-xs text-slate-500">Loading documents...</div>
                  ) : documents.length === 0 ? (
                    <div className="py-8 text-center text-xs text-slate-500">
                      No documents uploaded to this knowledge base yet.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {documents.map((doc) => (
                        <div
                          key={doc.id}
                          className="flex items-center justify-between p-3 rounded-lg bg-slate-800/40 border border-slate-700/60 hover:border-slate-600 transition-colors"
                        >
                          <div className="flex items-center gap-3 truncate">
                            {getFileIcon(doc.file_type)}
                            <div className="truncate">
                              <div className="text-sm font-medium text-slate-200 truncate">
                                {doc.original_filename}
                              </div>
                              <div className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
                                <span className="uppercase font-mono text-[10px] px-1.5 py-0.5 rounded bg-slate-700">
                                  {doc.file_type}
                                </span>
                                <span>{formatFileSize(doc.file_size)}</span>
                                <span>&bull;</span>
                                <span>
                                  {doc.document_metadata?.total_chunks ?? '-'} chunks indexed
                                </span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-3">
                            <span
                              className={`text-[10px] px-2 py-0.5 rounded-full font-mono uppercase font-semibold ${
                                doc.status === 'PROCESSED'
                                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                                  : doc.status === 'PROCESSING'
                                  ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                  : doc.status === 'FAILED'
                                  ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                  : 'bg-slate-500/10 text-slate-400 border border-slate-500/20'
                              }`}
                            >
                              {doc.status}
                            </span>

                            <button
                              onClick={() => handleInspectChunks(doc)}
                              className="p-1.5 text-slate-400 hover:text-indigo-300 hover:bg-slate-700 rounded transition-colors"
                              title="Inspect Extracted Chunks"
                            >
                              <Layers className="w-4 h-4" />
                            </button>

                            <button
                              onClick={() => handleDeleteDoc(doc)}
                              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-700 rounded transition-colors"
                              title="Delete Document &amp; Vectors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* New KB Modal */}
      {isKbModalOpen && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-md p-6 shadow-2xl">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-indigo-400" />
                Create Knowledge Base
              </h2>
              <button
                onClick={() => setIsKbModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateKb} className="mt-4 space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Knowledge Base Name *
                </label>
                <input
                  type="text"
                  required
                  value={newKbName}
                  onChange={(e) => setNewKbName(e.target.value)}
                  placeholder="e.g. HR Policies, Support Documentation"
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Description
                </label>
                <textarea
                  rows={3}
                  value={newKbDesc}
                  onChange={(e) => setNewKbDesc(e.target.value)}
                  placeholder="Description of contents in this knowledge collection..."
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="pt-4 border-t border-slate-800 flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setIsKbModalOpen(false)}
                  className="px-4 py-2 text-sm text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-lg shadow-sm"
                >
                  Create
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Chunks Inspector Modal */}
      {inspectingDoc && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-2xl p-6 shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800 shrink-0">
              <div>
                <h2 className="text-base font-bold text-white flex items-center gap-2">
                  <Layers className="w-5 h-5 text-indigo-400" />
                  Vector Chunks: {inspectingDoc.original_filename}
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">
                  Semantic chunks indexed into Qdrant with tenant payload isolation.
                </p>
              </div>
              <button
                onClick={() => setInspectingDoc(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto mt-4 space-y-3 pr-1">
              {chunksLoading ? (
                <div className="py-12 text-center text-xs text-slate-500">Loading vector chunks...</div>
              ) : chunks.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-500">No chunks found for this document.</div>
              ) : (
                chunks.map((chunk) => (
                  <div
                    key={chunk.id}
                    className="p-3.5 rounded-lg bg-slate-800/50 border border-slate-700/60 text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                      <span className="font-semibold text-indigo-400">Chunk #{chunk.chunk_index + 1}</span>
                      <span>~{chunk.token_count} tokens</span>
                    </div>
                    <p className="text-slate-200 whitespace-pre-wrap leading-relaxed font-mono text-[11px] bg-slate-950/60 p-2.5 rounded border border-slate-800">
                      {chunk.content}
                    </p>
                    {chunk.chunk_metadata && Object.keys(chunk.chunk_metadata).length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {Object.entries(chunk.chunk_metadata).map(([k, v]) => (
                          <span
                            key={k}
                            className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 text-[10px] text-slate-400 font-mono"
                          >
                            {k}: {String(v)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            <div className="pt-4 border-t border-slate-800 flex justify-end shrink-0">
              <button
                onClick={() => setInspectingDoc(null)}
                className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-white text-xs font-semibold rounded-lg"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
