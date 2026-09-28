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
  X,
  FileCode,
  FileSpreadsheet,
  Layers,
  Database,
  RotateCcw,
  Sparkles,
  Search,
  ExternalLink,
} from 'lucide-react';
import PageHeader from '@/components/ui/PageHeader';
import Button from '@/components/ui/Button';
import Badge from '@/components/ui/Badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import EmptyState from '@/components/ui/EmptyState';

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

  // Auto-polling for active background ingestion jobs
  useEffect(() => {
    const hasActiveDocs = documents.some(
      (d) => d.status === 'PROCESSING' || d.status === 'QUEUED'
    );
    if (!hasActiveDocs || !selectedKb) return;

    const interval = setInterval(() => {
      loadDocuments(selectedKb.id);
    }, 3000);

    return () => clearInterval(interval);
  }, [documents, selectedKb]);

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
      await api.uploadDocument(selectedKb.id, file);
      setSuccess(`Document "${file.name}" accepted. Ingestion processing in background.`);
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

  const handleRetryDoc = async (doc: DocumentItem) => {
    try {
      setError(null);
      await api.retryDocumentIngestion(doc.id);
      setSuccess(`Re-queued ingestion for "${doc.original_filename}"`);
      if (selectedKb) {
        await loadDocuments(selectedKb.id);
      }
    } catch (err: any) {
      setError(err.message || 'Retry failed');
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
    if (ft === 'pdf') return <FileText className="w-4 h-4 text-[#FF9D00]" />;
    if (ft === 'docx') return <FileText className="w-4 h-4 text-blue-400" />;
    if (ft === 'md') return <FileCode className="w-4 h-4 text-emerald-400" />;
    if (ft === 'csv') return <FileSpreadsheet className="w-4 h-4 text-amber-400" />;
    return <FileText className="w-4 h-4 text-[#A1A1AA]" />;
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Knowledge Base Management"
        description="Upload company documents, policies, and datasets to index semantic vector chunks into Qdrant & BM25 sparse indexes."
        badge={<Badge variant="orange">Hybrid Retrieval RAG</Badge>}
        actions={
          <Button
            variant="orange"
            size="sm"
            icon={Plus}
            onClick={() => setIsKbModalOpen(true)}
          >
            New Knowledge Base
          </Button>
        }
      />

      {/* Notifications */}
      {error && (
        <div className="p-3.5 rounded-lg bg-rose-950/40 border border-rose-900/60 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-3.5 rounded-lg bg-emerald-950/40 border border-emerald-900/60 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
          <span>{success}</span>
        </div>
      )}

      {/* Main Content Layout */}
      {loading ? (
        <div className="py-20 text-center text-xs text-[#737373] font-mono">
          Loading knowledge infrastructure...
        </div>
      ) : knowledgeBases.length === 0 ? (
        <EmptyState
          icon={BookOpen}
          title="No Knowledge Bases Found"
          description="Create your first company knowledge base to begin uploading documentation, PDFs, and policy guidelines."
          actionText="Create Knowledge Base"
          actionIcon={Plus}
          onAction={() => setIsKbModalOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Knowledge Bases Sidebar List */}
          <div className="lg:col-span-1 space-y-2">
            <div className="flex items-center justify-between mb-3 px-1">
              <h2 className="text-[11px] font-mono uppercase tracking-wider text-[#737373]">
                Knowledge Bases ({knowledgeBases.length})
              </h2>
            </div>
            <div className="space-y-1.5">
              {knowledgeBases.map((kb) => {
                const isSelected = selectedKb?.id === kb.id;
                return (
                  <button
                    key={kb.id}
                    onClick={() => setSelectedKb(kb)}
                    className={`w-full text-left p-3.5 rounded-lg border transition-all flex items-start justify-between ${
                      isSelected
                        ? 'bg-[#151515] border-[#FF9D00]/40 text-[#F5F5F5] shadow-sm'
                        : 'bg-[#101010] border-[#262626] text-[#A1A1AA] hover:bg-[#151515] hover:border-[#333333] hover:text-[#F5F5F5]'
                    }`}
                  >
                    <div className="truncate pr-2">
                      <div className="font-medium text-xs truncate text-[#F5F5F5]">{kb.name}</div>
                      {kb.description && (
                        <div className="text-[11px] text-[#737373] truncate mt-0.5">{kb.description}</div>
                      )}
                    </div>
                    {isSelected && (
                      <span className="w-1.5 h-1.5 rounded-full bg-[#FF9D00] shrink-0 mt-1.5 shadow-[0_0_8px_rgba(255,157,0,0.6)]" />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Selected Knowledge Base & Documents Panel */}
          <div className="lg:col-span-3 space-y-5">
            {selectedKb ? (
              <Card>
                <CardHeader>
                  <div>
                    <h2 className="text-sm font-semibold font-display text-[#F5F5F5] flex items-center gap-2">
                      <BookOpen className="w-4 h-4 text-[#FF9D00]" />
                      <span>{selectedKb.name}</span>
                    </h2>
                    {selectedKb.description && (
                      <p className="text-xs text-[#737373] mt-0.5">{selectedKb.description}</p>
                    )}
                  </div>
                  <button
                    onClick={() => handleDeleteKb(selectedKb)}
                    className="p-1.5 text-[#737373] hover:text-rose-400 hover:bg-[#1A1A1A] rounded transition-colors"
                    title="Delete Knowledge Base"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </CardHeader>

                <CardContent className="space-y-6">
                  {/* Upload Box */}
                  <div className="p-7 border border-dashed border-[#262626] hover:border-[#FF9D00]/40 rounded-lg bg-[#0B0B0B] text-center transition-all">
                    <div className="w-10 h-10 rounded-lg bg-[#151515] border border-[#262626] flex items-center justify-center mx-auto mb-3">
                      <UploadCloud className="w-5 h-5 text-[#FF9D00]" />
                    </div>
                    <h3 className="text-xs font-medium text-[#F5F5F5]">
                      Upload documents to index into hybrid vector search
                    </h3>
                    <p className="text-[11px] text-[#737373] mt-1">
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
                      className={`mt-4 inline-flex items-center gap-2 px-4 py-2 bg-[#FF9D00] hover:bg-[#FF6A00] text-black text-xs font-semibold rounded-lg cursor-pointer transition-colors shadow-sm ${
                        uploading ? 'opacity-50 pointer-events-none' : ''
                      }`}
                    >
                      {uploading ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Extracting & Vectorizing Chunks...</span>
                        </>
                      ) : (
                        <>
                          <Plus className="w-3.5 h-3.5" />
                          <span>Select File to Ingest</span>
                        </>
                      )}
                    </label>
                  </div>

                  {/* Document List */}
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-[11px] font-mono text-[#737373] uppercase tracking-wider">
                        Indexed Documents ({documents.length})
                      </h3>
                    </div>

                    {docsLoading ? (
                      <div className="py-8 text-center text-xs text-[#737373] font-mono">Loading documents...</div>
                    ) : documents.length === 0 ? (
                      <div className="text-center py-8 text-xs text-[#737373] border border-dashed border-[#262626] rounded-lg">
                        No documents uploaded to this knowledge base yet.
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {documents.map((doc) => (
                          <div
                            key={doc.id}
                            className="p-3.5 rounded-lg bg-[#0B0B0B] border border-[#262626] flex flex-col sm:flex-row sm:items-center justify-between gap-3 transition-colors hover:border-[#333333]"
                          >
                            <div className="flex items-center gap-3">
                              <div className="p-2 rounded bg-[#151515] border border-[#262626]">
                                {getFileIcon(doc.file_type)}
                              </div>
                              <div>
                                <div className="text-xs font-medium text-[#F5F5F5]">{doc.original_filename}</div>
                                <div className="flex items-center gap-2 text-[10px] text-[#737373] font-mono mt-0.5">
                                  <span>{formatFileSize(doc.file_size)}</span>
                                  <span>&bull;</span>
                                  <span>{doc.chunk_count || 0} chunks</span>
                                  <span>&bull;</span>
                                  <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center gap-2 shrink-0">
                              <Badge
                                variant={
                                  doc.status === 'PROCESSED'
                                    ? 'forest'
                                    : doc.status === 'PROCESSING' || doc.status === 'QUEUED' || doc.status === 'UPLOADED'
                                    ? 'amber'
                                    : 'rose'
                                }
                                dot
                              >
                                {doc.status}
                              </Badge>

                              {doc.status === 'FAILED' && (
                                <button
                                  onClick={() => handleRetryDoc(doc)}
                                  className="p-1.5 text-amber-400 hover:bg-[#1A1A1A] rounded transition-colors"
                                  title="Retry Ingestion"
                                >
                                  <RotateCcw className="w-3.5 h-3.5" />
                                </button>
                              )}

                              {doc.status === 'PROCESSED' && (
                                <button
                                  onClick={() => handleInspectChunks(doc)}
                                  className="px-2.5 py-1 text-[11px] bg-[#151515] hover:bg-[#1E1E1E] border border-[#262626] text-[#A1A1AA] hover:text-[#F5F5F5] rounded font-medium transition-colors"
                                  title="Inspect Chunks"
                                >
                                  Inspect Chunks
                                </button>
                              )}

                              <button
                                onClick={() => handleDeleteDoc(doc)}
                                className="p-1.5 text-[#737373] hover:text-rose-400 hover:bg-[#1A1A1A] rounded transition-colors"
                                title="Delete Document"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ) : null}
          </div>
        </div>
      )}

      {/* New KB Modal */}
      {isKbModalOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262626]">
              <h3 className="text-sm font-semibold font-display text-[#F5F5F5] flex items-center gap-2">
                <BookOpen className="w-4 h-4 text-[#FF9D00]" />
                <span>Create Knowledge Base</span>
              </h3>
              <button
                onClick={() => setIsKbModalOpen(false)}
                className="text-[#737373] hover:text-[#F5F5F5] p-1 rounded hover:bg-[#1A1A1A]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateKb} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                  Knowledge Base Name *
                </label>
                <input
                  type="text"
                  required
                  value={newKbName}
                  onChange={(e) => setNewKbName(e.target.value)}
                  placeholder="e.g. HR Policies, Product Manuals"
                  className="w-full px-3.5 py-2 bg-[#050505] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] placeholder-[#737373] focus:outline-none focus:border-[#FF9D00]"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-[#A1A1AA] mb-1.5">
                  Description
                </label>
                <input
                  type="text"
                  value={newKbDesc}
                  onChange={(e) => setNewKbDesc(e.target.value)}
                  placeholder="Scope of documents in this collection"
                  className="w-full px-3.5 py-2 bg-[#050505] border border-[#262626] rounded-lg text-xs text-[#F5F5F5] placeholder-[#737373] focus:outline-none focus:border-[#FF9D00]"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[#262626]">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsKbModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="orange" size="sm">
                  Create Knowledge Base
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Chunks Inspector Modal */}
      {inspectingDoc && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#101010] border border-[#262626] rounded-xl w-full max-w-2xl p-6 shadow-2xl max-h-[85vh] flex flex-col space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#262626] shrink-0">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-[#FF9D00]" />
                <h3 className="text-sm font-semibold font-display text-[#F5F5F5]">
                  Chunk Inspector: <span className="text-[#A1A1AA] font-normal">{inspectingDoc.original_filename}</span>
                </h3>
              </div>
              <button
                onClick={() => setInspectingDoc(null)}
                className="text-[#737373] hover:text-[#F5F5F5] p-1 rounded hover:bg-[#1A1A1A]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-1">
              {chunksLoading ? (
                <div className="py-12 text-center text-xs text-[#737373] font-mono">Loading vector chunks...</div>
              ) : chunks.length === 0 ? (
                <div className="py-12 text-center text-xs text-[#737373]">No chunks generated for this document.</div>
              ) : (
                chunks.map((chunk, idx) => (
                  <div
                    key={chunk.id || idx}
                    className="p-3.5 rounded-lg bg-[#0B0B0B] border border-[#262626] text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between text-[11px] text-[#737373] font-mono">
                      <span className="text-[#FF9D00]">Chunk #{chunk.chunk_index !== undefined ? chunk.chunk_index : idx + 1}</span>
                      <span>Page {chunk.page_number || chunk.chunk_metadata?.page_number || 1} &bull; {chunk.token_count || 0} tokens</span>
                    </div>
                    <div className="p-3 rounded bg-[#050505] border border-[#262626] text-[#D4D4D8] font-mono text-[11px] leading-relaxed whitespace-pre-wrap">
                      {chunk.content}
                    </div>
                  </div>
                ))
              )}
            </div>

            <div className="pt-3 border-t border-[#262626] flex justify-end shrink-0">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setInspectingDoc(null)}
              >
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
