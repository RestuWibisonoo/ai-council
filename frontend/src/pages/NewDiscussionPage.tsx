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
  AlertCircle
} from 'lucide-react';
import { api, ProviderConfig, DocumentItem } from '../services/api';

export const NewDiscussionPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const defaultMode = (searchParams.get('mode') as 'parallel' | 'debate' | 'research') || 'parallel';

  const [query, setQuery] = useState('');
  const [title, setTitle] = useState('');
  const [mode, setMode] = useState<'parallel' | 'debate' | 'research'>(defaultMode);
  const [maxRounds, setMaxRounds] = useState<number>(2);
  const [selectedProviders, setSelectedProviders] = useState<string[]>(['chatgpt', 'claude', 'gemini']);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);

  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [provs, docs] = await Promise.all([
          api.getProviders(),
          api.getDocuments(),
        ]);
        setProviders(provs);
        setDocuments(docs);
      } catch (err) {
        console.error('Failed to load initial configs:', err);
      }
    };
    loadData();
  }, []);

  const toggleProvider = (id: string) => {
    setSelectedProviders((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
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
    if (selectedProviders.length === 0) {
      setError('Pilih minimal satu AI dewan untuk berdiskusi.');
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const run = await api.createDiscussion({
        query: query.trim(),
        mode,
        selected_providers: selectedProviders,
        max_rounds: mode === 'debate' ? maxRounds : 1,
        linked_document_ids: selectedDocIds,
        conversation_title: title.trim() || undefined,
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

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-black text-white tracking-tight">
          Mulai Diskusi AI Council Baru
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Kumpulkan jawaban beragam model AI, jalankan kritik silang, dan hasilkan sintesis moderator yang objektif.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-300 text-sm flex items-center gap-2">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-7">
        {/* Mode Selector */}
        <div>
          <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2.5">
            Pilih Mode Diskusi
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
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
                Kirim pertanyaan ke seluruh AI terpilih dan bandingkan jawaban secara berdampingan.
              </p>
            </div>

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
                <h3 className="font-bold text-sm text-white">AI Debate</h3>
              </div>
              <p className="text-xs text-slate-400 leading-relaxed">
                4 Tahap: Analisis awal, kritik silang (fallacies & unverified claims), sanggahan, dan sintesis akhir.
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
                Diskusi terstruktur dengan integrasi potongan dokumen PDF lokal dan catatan NotebookLM.
              </p>
            </div>
          </div>
        </div>

        {/* Input Question */}
        <div className="space-y-2">
          <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider">
            Topik / Pertanyaan Diskusi
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tuliskan pertanyaan, studi kasus, atau dilema arsitektur yang ingin didiskusikan oleh dewan AI..."
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
            Judul Sesi Percakapan (Opsional)
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Contoh: Diskusi Arsitektur Database Q4"
            className="w-full px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        {/* Provider Selection */}
        <div>
          <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2.5">
            Pilih Anggota Dewan AI
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {providers.map((p) => {
              const isSelected = selectedProviders.includes(p.id);
              return (
                <div
                  key={p.id}
                  onClick={() => toggleProvider(p.id)}
                  className={`p-3.5 rounded-2xl border cursor-pointer transition flex items-center justify-between ${
                    isSelected
                      ? 'bg-slate-900 border-emerald-500/80 shadow-md shadow-emerald-500/10'
                      : 'bg-slate-950/60 border-slate-800 opacity-60 hover:opacity-100'
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded-lg bg-slate-800 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-slate-300" />
                    </div>
                    <div>
                      <h4 className="font-bold text-sm text-slate-200">{p.display_name}</h4>
                      <p className="text-[10px] text-slate-400">
                        {p.default_mode === 'api' ? 'Official API' : 'Manual Bridge'}
                      </p>
                    </div>
                  </div>
                  <div
                    className={`w-5 h-5 rounded-md flex items-center justify-center border transition ${
                      isSelected
                        ? 'bg-emerald-500 border-emerald-500 text-slate-950'
                        : 'border-slate-700 bg-slate-800'
                    }`}
                  >
                    {isSelected && <Check className="w-3.5 h-3.5 stroke-[3]" />}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Rounds Selector (Only for Debate) */}
        {mode === 'debate' && (
          <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800">
            <label className="block text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
              Jumlah Putaran Debat (Maksimal 3)
            </label>
            <div className="flex items-center gap-3">
              {[1, 2, 3].map((r) => (
                <button
                  key={r}
                  type="button"
                  onClick={() => setMaxRounds(r)}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition ${
                    maxRounds === r
                      ? 'bg-amber-500 text-slate-950 shadow-md shadow-amber-500/20'
                      : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
                  }`}
                >
                  {r} Putaran
                </button>
              ))}
              <span className="text-xs text-slate-400 ml-2">
                Setiap putaran mencakup kritik silang dan sanggahan sebelum sintesis akhir.
              </span>
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
                {selectedDocIds.length} dipilih
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto p-1">
              {documents.map((d) => {
                const isSelected = selectedDocIds.includes(d.id);
                return (
                  <div
                    key={d.id}
                    onClick={() => toggleDoc(d.id)}
                    className={`p-3 rounded-xl border cursor-pointer transition flex items-center justify-between text-xs ${
                      isSelected
                        ? 'bg-indigo-950/40 border-indigo-500/60 text-slate-200'
                        : 'bg-slate-900/40 border-slate-800 text-slate-400 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <FileText className="w-4 h-4 shrink-0 text-indigo-400" />
                      <span className="truncate font-medium">{d.title}</span>
                      <span className="text-[10px] text-slate-500 font-mono">
                        ({d.total_pages} hal)
                      </span>
                    </div>
                    <div
                      className={`w-4 h-4 rounded flex items-center justify-center border shrink-0 ${
                        isSelected ? 'bg-indigo-500 border-indigo-500 text-white' : 'border-slate-700'
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

        {/* Submit Launch Button */}
        <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-4">
          <button
            type="button"
            onClick={() => navigate('/')}
            className="px-5 py-2.5 rounded-xl text-slate-400 hover:text-slate-200 text-sm font-semibold transition"
          >
            Batal
          </button>
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="flex items-center gap-2.5 px-6 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 disabled:cursor-not-allowed text-slate-950 font-bold text-sm transition shadow-lg shadow-emerald-500/25"
          >
            <Play className="w-4 h-4 fill-current" />
            <span>{isLoading ? 'Menyiapkan Diskusi...' : 'Mulai Diskusi AI Council'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
