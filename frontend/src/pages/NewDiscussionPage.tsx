import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Sparkles,
  Columns,
  Flame,
  FolderKanban,
  FileText,
  Play,
  Check,
  Bot,
  AlertCircle,
  ShieldCheck,
  RefreshCw,
  Cpu,
  Layers,
  Zap
} from 'lucide-react';
import { api, ProviderConfig, DocumentItem, CatalogModel } from '../services/api';

export const NewDiscussionPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const defaultMode = (searchParams.get('mode') as 'parallel' | 'debate' | 'research') || 'debate';

  const [query, setQuery] = useState('');
  const [title, setTitle] = useState('');
  const [mode, setMode] = useState<'parallel' | 'debate' | 'research'>(defaultMode);
  const [maxRounds, setMaxRounds] = useState<number>(2);
  const [autoRun, setAutoRun] = useState<boolean>(true);
  const [zeroCostMode, setZeroCostMode] = useState<boolean>(true);

  // Selected participant models/providers
  const [selectedModels, setSelectedModels] = useState<string[]>([
    'openrouter:deepseek/deepseek-r1:free',
    'openrouter:meta-llama/llama-3.3-70b-instruct:free',
    'openrouter:qwen/qwen-2.5-72b-instruct:free'
  ]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);

  const [catalogModels, setCatalogModels] = useState<CatalogModel[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [activeFamilyFilter, setActiveFamilyFilter] = useState<string>('all');
  const [isRefreshingCatalog, setIsRefreshingCatalog] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [docs, catalog] = await Promise.all([
        api.getDocuments().catch(() => []),
        api.getModelsCatalog().catch(() => []),
      ]);
      setDocuments(docs);
      setCatalogModels(catalog);
    } catch (err) {
      console.error('Failed to load initial configs:', err);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRefreshCatalog = async () => {
    setIsRefreshingCatalog(true);
    try {
      const catalog = await api.getModelsCatalog();
      setCatalogModels(catalog);
    } catch (err: any) {
      setError(err.message || 'Gagal menyegarkan katalog model');
    } finally {
      setIsRefreshingCatalog(false);
    }
  };

  const toggleModel = (modelId: string) => {
    setSelectedModels((prev) =>
      prev.includes(modelId) ? prev.filter((m) => m !== modelId) : [...prev, modelId]
    );
  };

  const toggleDoc = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      setError('Harap masukkan pertanyaan atau topik diskusi.');
      return;
    }
    if (selectedModels.length === 0) {
      setError('Pilih minimal satu AI dewan untuk berdiskusi.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const run = await api.createDiscussion({
        query: query.trim(),
        mode,
        selected_providers: selectedModels,
        max_rounds: mode === 'debate' ? maxRounds : 1,
        linked_document_ids: selectedDocIds,
        conversation_title: title.trim() || undefined,
        auto_run: mode === 'debate' ? autoRun : false,
        zero_cost_mode: zeroCostMode,
      });
      navigate(`/discussions/${run.id}`);
    } catch (err: any) {
      setError(err.message || 'Gagal memulai diskusi');
      setIsLoading(false);
    }
  };

  const suggestionPrompts = [
    'Bandingkan kelebihan dan kekurangan arsitektur Microservices vs Monolith modular.',
    'Evaluasi keamanan penggunaan LLM pada data sensitif perbankan dan risiko kebocoran.',
    'Bagaimana strategi mitigasi teknis saat migrasi sistem database dari SQLite ke PostgreSQL?',
    'Analisis efektivitas teknik RAG (Retrieval-Augmented Generation) dibanding Fine-Tuning.',
  ];

  // Filter models based on zero-cost mode and family
  const filteredCatalog = catalogModels.filter((m) => {
    if (zeroCostMode && !m.is_zero_cost) return false;
    if (activeFamilyFilter === 'all') return true;
    if (activeFamilyFilter === 'DeepSeek') return m.family.includes('DeepSeek');
    if (activeFamilyFilter === 'Qwen') return m.family.includes('Qwen');
    if (activeFamilyFilter === 'Meta Llama') return m.family.includes('Llama');
    if (activeFamilyFilter === 'Lokal') return m.provider === 'ollama';
    if (activeFamilyFilter === 'Google') return m.family.includes('Gemini');
    return true;
  });

  const estimatedRequests = selectedModels.length * (mode === 'debate' ? (maxRounds * 2 + 1) : 1);

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-2xl font-black text-white tracking-tight">
            Mulai Diskusi AI Council Baru
          </h1>
          <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
            Free Multi-AI Platform
          </span>
        </div>
        <p className="text-sm text-slate-400 mt-1">
          Jalankan debat otomatis multi-model menggunakan API gratis (DeepSeek, Qwen, Meta Llama, Ollama Lokal, Gemini).
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-7">
        {/* Zero Cost Mode Banner & Safety Toggle */}
        <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-slate-900 border border-emerald-500/30 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-white">Zero-Cost Mode</h4>
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  100% BEBAS BIAYA API
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Secara ketat memverifikasi harga $0.00 dan menolak pemanggilan model berbayar yang tidak disengaja.
              </p>
            </div>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={zeroCostMode}
              onChange={(e) => setZeroCostMode(e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-500"></div>
          </label>
        </div>

        {/* Mode Selector */}
        <div>
          <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2.5">
            Pilih Mode Diskusi
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div
              onClick={() => setMode('debate')}
              className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                mode === 'debate'
                  ? 'bg-amber-500/10 border-amber-500 shadow-md shadow-amber-500/10'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <Flame className={`w-4 h-4 ${mode === 'debate' ? 'text-amber-400' : 'text-slate-400'}`} />
                <h3 className="font-bold text-sm text-white">AI Debate (Multi-Stage)</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                4 Tahap: Analisis awal, kritik silang antarmodel, sanggahan argumentatif, dan sintesis akhir moderator.
              </p>
            </div>

            <div
              onClick={() => setMode('parallel')}
              className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                mode === 'parallel'
                  ? 'bg-emerald-500/10 border-emerald-500 shadow-md shadow-emerald-500/10'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <Columns className={`w-4 h-4 ${mode === 'parallel' ? 'text-emerald-400' : 'text-slate-400'}`} />
                <h3 className="font-bold text-sm text-white">Parallel Chat</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Kirim pertanyaan ke seluruh AI terpilih secara serentak dan bandingkan jawaban secara berdampingan.
              </p>
            </div>

            <div
              onClick={() => setMode('research')}
              className={`p-4 rounded-2xl border cursor-pointer transition-all ${
                mode === 'research'
                  ? 'bg-indigo-500/10 border-indigo-500 shadow-md shadow-indigo-500/10'
                  : 'bg-slate-900/60 border-slate-800 hover:border-slate-700'
              }`}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <FolderKanban className={`w-4 h-4 ${mode === 'research' ? 'text-indigo-400' : 'text-slate-400'}`} />
                <h3 className="font-bold text-sm text-white">Research Workspace</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                Diskusi terstruktur dengan integrasi kutipan dokumen PDF lokal dan catatan riset terpadu.
              </p>
            </div>
          </div>
        </div>

        {/* Input Question */}
        <div className="space-y-2">
          <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
            Topik / Pertanyaan Penelitian
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tuliskan topik, pertanyaan, atau dilema arsitektur yang ingin diperdebatkan oleh dewan AI..."
            rows={5}
            className="w-full px-4 py-3.5 rounded-2xl bg-slate-900/90 border border-slate-800 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition shadow-inner font-sans"
            required
          />

          {/* Quick Suggestions */}
          <div className="pt-1">
            <span className="text-[11px] text-slate-400 font-medium mr-2">Contoh topik:</span>
            <div className="flex flex-wrap gap-1.5 mt-1.5">
              {suggestionPrompts.map((s, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => setQuery(s)}
                  className="px-2.5 py-1 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 text-xs transition text-left"
                >
                  {s.slice(0, 48)}...
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Title (Optional) */}
        <div>
          <label className="block text-xs font-semibold text-slate-400 mb-1.5">
            Judul Sesi Diskusi (Opsional)
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Contoh: Evaluasi High Availability Server Proxmox vs Ceph"
            className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        {/* Model Roster & Free Catalog Selection */}
        <div>
          <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
            <div>
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider block">
                Pilih Anggota Dewan AI ({selectedModels.length} Model Dipilih)
              </label>
              <span className="text-xs text-slate-500">
                Pilih model dari keluarga yang berbeda untuk debat yang kaya sudut pandang.
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleRefreshCatalog}
                disabled={isRefreshingCatalog}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-800 text-xs transition disabled:opacity-50"
                title="Perbarui daftar model gratis dari API OpenRouter"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isRefreshingCatalog ? 'animate-spin' : ''}`} />
                <span>Segarkan Katalog</span>
              </button>
            </div>
          </div>

          {/* Family Filters */}
          <div className="flex flex-wrap gap-1.5 mb-3.5">
            {[
              { id: 'all', label: 'Semua Model' },
              { id: 'DeepSeek', label: 'DeepSeek' },
              { id: 'Qwen', label: 'Qwen / Alibaba' },
              { id: 'Meta Llama', label: 'Meta Llama' },
              { id: 'Google', label: 'Google Gemini' },
              { id: 'Lokal', label: 'Ollama Lokal' },
            ].map((f) => (
              <button
                key={f.id}
                type="button"
                onClick={() => setActiveFamilyFilter(f.id)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition ${
                  activeFamilyFilter === f.id
                    ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                    : 'bg-slate-900/80 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          {/* Model Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {filteredCatalog.map((m) => {
              const isSelected = selectedModels.includes(m.id);
              return (
                <div
                  key={m.id}
                  onClick={() => toggleModel(m.id)}
                  className={`p-3.5 rounded-2xl border cursor-pointer transition flex flex-col justify-between ${
                    isSelected
                      ? 'bg-slate-900 border-emerald-500/80 shadow-md shadow-emerald-500/10'
                      : 'bg-slate-950/60 border-slate-800/80 opacity-70 hover:opacity-100 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center shrink-0">
                        <Bot className="w-4 h-4 text-slate-300" />
                      </div>
                      <div>
                        <h4 className="font-bold text-xs text-slate-100 leading-snug line-clamp-1">{m.name}</h4>
                        <span className="text-[10px] text-slate-400 font-mono">{m.provider_name}</span>
                      </div>
                    </div>
                    <div
                      className={`w-4 h-4 rounded-md flex items-center justify-center border shrink-0 transition ${
                        isSelected
                          ? 'bg-emerald-500 border-emerald-500 text-slate-950'
                          : 'border-slate-700 bg-slate-800'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[10px] mt-2 pt-2 border-t border-slate-800/80">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 font-medium">
                      {m.family}
                    </span>
                    <span className="px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-300 font-bold border border-emerald-500/30">
                      GRATIS (0 USD)
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Debate Automation Options (Debate Mode Only) */}
        {mode === 'debate' && (
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
                    Otomasi Debat (1-Klik Auto-Run)
                  </h4>
                </div>
                <p className="text-xs text-slate-400 mt-0.5">
                  Eksekusi otomatis penuh: Analisis Awal ➔ Kritik Silang ➔ Sanggahan ➔ Sintesis Moderator.
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoRun}
                  onChange={(e) => setAutoRun(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-amber-500"></div>
              </label>
            </div>

            {/* Rounds Selector */}
            <div className="pt-2 border-t border-slate-800/80">
              <label className="block text-xs font-semibold text-slate-300 mb-2">
                Jumlah Putaran Debat:
              </label>
              <div className="flex items-center gap-2.5">
                {[1, 2, 3].map((r) => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setMaxRounds(r)}
                    className={`px-3.5 py-1.5 rounded-xl text-xs font-bold transition ${
                      maxRounds === r
                        ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                        : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                    }`}
                  >
                    {r} Putaran
                  </button>
                ))}
                <span className="text-[11px] text-slate-400 ml-2">
                  (Maksimal 3 putaran kritik & sanggahan)
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Linked Documents Context */}
        {documents.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                Sertakan Dokumen Riset (Konteks Lokal)
              </label>
              <span className="text-xs text-slate-400">
                {selectedDocIds.length} dokumen terpilih
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {documents.map((doc) => {
                const isSelected = selectedDocIds.includes(doc.id);
                return (
                  <div
                    key={doc.id}
                    onClick={() => toggleDoc(doc.id)}
                    className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between ${
                      isSelected
                        ? 'bg-indigo-950/30 border-indigo-500/60 text-indigo-200'
                        : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <FileText className="w-4 h-4 shrink-0 text-slate-400" />
                      <div className="truncate">
                        <p className="text-xs font-medium text-slate-200 truncate">{doc.title}</p>
                        <p className="text-[10px] text-slate-500">
                          {doc.file_type.toUpperCase()} • {doc.total_pages} halaman
                        </p>
                      </div>
                    </div>
                    <div
                      className={`w-4 h-4 rounded flex items-center justify-center border shrink-0 ${
                        isSelected
                          ? 'bg-indigo-500 border-indigo-500 text-white'
                          : 'border-slate-700'
                      }`}
                    >
                      {isSelected && <Check className="w-3 h-3 stroke-[3]" />}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Summary & Submit Button */}
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
          <div className="text-xs text-slate-400 space-y-0.5">
            <p>
              Dewan: <strong className="text-slate-200">{selectedModels.length} model</strong> terpilih.
            </p>
            <p>
              Estimasi Request: <strong className="text-slate-200">~{estimatedRequests} panggilan API</strong> (Estimasi Biaya: <strong className="text-emerald-400">$0.00 USD / Rp 0</strong>).
            </p>
          </div>

          <button
            type="submit"
            disabled={isLoading || selectedModels.length === 0}
            className="flex items-center gap-2 px-6 py-3 rounded-xl font-bold text-sm bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 transition shadow-lg shadow-emerald-500/20 disabled:opacity-50"
          >
            {isLoading ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-slate-950 border-t-transparent animate-spin"></div>
                <span>Menyiapkan Debat...</span>
              </>
            ) : autoRun && mode === 'debate' ? (
              <>
                <Zap className="w-4 h-4 fill-current" />
                <span>Mulai Debat Otomatis Sekarang</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Mulai Diskusi</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
