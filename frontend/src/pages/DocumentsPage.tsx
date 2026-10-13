import React, { useState, useEffect } from 'react';
import {
  FileText,
  Upload,
  Search,
  Trash2,
  FileCheck,
  BookOpen,
  AlertCircle,
  CheckCircle,
  ExternalLink
} from 'lucide-react';
import { api, DocumentItem, DocumentSearchResult } from '../services/api';

export const DocumentsPage: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<DocumentSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const loadDocuments = async () => {
    try {
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);
    try {
      await api.uploadDocument(file);
      await loadDocuments();
      e.target.value = '';
    } catch (err: any) {
      setUploadError(err.message || 'Gagal mengunggah dokumen.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string, title: string) => {
    if (confirm(`Apakah Anda yakin ingin menghapus dokumen "${title}" beserta indeksnya?`)) {
      try {
        await api.deleteDocument(docId);
        await loadDocuments();
      } catch (err: any) {
        alert(err.message || 'Gagal menghapus dokumen.');
      }
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    setIsSearching(true);
    try {
      const res = await api.searchDocuments(searchQuery.trim());
      setSearchResults(res);
    } catch (err) {
      console.error('Search error:', err);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      {/* Header & Upload Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 text-xs font-semibold mb-2">
            <FileText className="w-3.5 h-3.5" />
            <span>Knowledge Engine Lokal</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Dokumen & Sumber Penelitian
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Ekstrak teks PDF via PyMuPDF, simpan potongan per halaman, dan cari kutipan empiris untuk dijadikan konteks AI.
          </p>
        </div>

        <div>
          <label className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition cursor-pointer shadow-lg shadow-emerald-500/20">
            <Upload className="w-4 h-4" />
            <span>{isUploading ? 'Mengekstrak PDF...' : 'Unggah PDF / TXT / MD'}</span>
            <input
              type="file"
              accept=".pdf,.txt,.md"
              onChange={handleFileUpload}
              disabled={isUploading}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {uploadError && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{uploadError}</span>
        </div>
      )}

      {/* Local Text Search Bar */}
      <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md space-y-4">
        <form onSubmit={handleSearch} className="flex gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Cari kata kunci, topik, atau nomor referensi di seluruh dokumen..."
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
          <button
            type="submit"
            disabled={isSearching}
            className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold transition"
          >
            {isSearching ? 'Mencari...' : 'Uji Pencarian'}
          </button>
        </form>

        {/* Search Results Display */}
        {searchResults.length > 0 && (
          <div className="mt-4 pt-4 border-t border-slate-800 space-y-3">
            <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
              Hasil Kutipan Terverifikasi ({searchResults.length} potongan ditemukan):
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {searchResults.map((res, i) => (
                <div
                  key={i}
                  className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between text-indigo-400 font-semibold">
                    <span className="truncate">{res.document_title}</span>
                    <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-[10px]">
                      Halaman {res.page_number}
                    </span>
                  </div>
                  <p className="text-slate-300 italic font-serif leading-relaxed line-clamp-4">
                    "{res.content}"
                  </p>
                  <div className="flex items-center justify-between pt-1 text-[10px] text-slate-500">
                    <span>Relevansi: {res.relevance_score}</span>
                    <span className="text-emerald-400 font-semibold">Kutipan Asli Dokumen</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Document Library List */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 backdrop-blur-md">
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
          <h2 className="text-base font-bold text-white">Daftar Dokumen Tersimpan</h2>
          <span className="text-xs text-slate-400">Total: {documents.length} dokumen</span>
        </div>

        {documents.length === 0 ? (
          <div className="py-12 text-center text-slate-500">
            <FileText className="w-10 h-10 mx-auto mb-2 opacity-40" />
            <p className="text-sm font-medium">Belum ada dokumen yang diunggah</p>
            <p className="text-xs mt-1">Unggah PDF penelitian atau artikel untuk memulai.</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="py-4 flex items-center justify-between hover:bg-slate-900/50 px-2 rounded-xl transition"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-indigo-400" />
                  </div>
                  <div>
                    <h3 className="font-bold text-sm text-slate-200">{doc.title}</h3>
                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                      <span className="uppercase font-mono text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                        {doc.file_type}
                      </span>
                      <span>{doc.total_pages} halaman</span>
                      <span>{doc.total_chunks} potongan indeks</span>
                      <span>{(doc.file_size_bytes / 1024).toFixed(1)} KB</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleDelete(doc.id, doc.title)}
                    className="p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition"
                    title="Hapus dokumen"
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
  );
};
