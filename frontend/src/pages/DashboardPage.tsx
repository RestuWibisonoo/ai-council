import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  MessageSquare,
  FileText,
  KeyRound,
  Coins,
  ArrowRight,
  Flame,
  Columns,
  ExternalLink,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';
import { api, ConversationItem, ProviderConfig, UsageSummary } from '../services/api';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [docCount, setDocCount] = useState<number>(0);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [convs, provs, docs, usg] = await Promise.all([
          api.getConversations(),
          api.getProviders(),
          api.getDocuments(),
          api.getUsageSummary(),
        ]);
        setConversations(convs.slice(0, 5));
        setProviders(provs);
        setDocCount(docs.length);
        setUsage(usg);
      } catch (err) {
        console.error('Failed to load dashboard data:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Hero Welcome Banner */}
      <div className="rounded-3xl bg-gradient-to-r from-emerald-950/70 via-slate-900 to-indigo-950/50 border border-emerald-500/30 p-8 shadow-2xl relative overflow-hidden backdrop-blur-xl">
        <div className="absolute -right-10 -bottom-10 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-xs font-semibold mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Council v1.0 — Siap Berjalan Tanpa API Key</span>
          </div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight leading-snug">
            Multi-AI Discussion & Research Workspace
          </h1>
          <p className="mt-2 text-slate-300 text-sm leading-relaxed">
            Kelola diskusi, debat komparatif, kritik silang, dan konsensus bersama DeepSeek, Qwen, Meta Llama, Gemini, dan Ollama Lokal dalam satu antarmuka terpadu.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              onClick={() => navigate('/new-discussion')}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm transition shadow-lg shadow-emerald-500/25"
            >
              <span>Mulai Diskusi Baru</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => navigate('/debate')}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700 text-slate-200 font-semibold text-sm transition border border-slate-700"
            >
              <Flame className="w-4 h-4 text-amber-400" />
              <span>Sesi AI Debate</span>
            </button>
          </div>
        </div>
      </div>

      {/* Stats Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Total Diskusi</span>
            <MessageSquare className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">{conversations.length}</div>
          <p className="text-[11px] text-slate-500 mt-1">Sesi percakapan tersimpan</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Dokumen Penelitian</span>
            <FileText className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white">{docCount}</div>
          <p className="text-[11px] text-slate-500 mt-1">PDF & teks siap dijadikan konteks</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Provider Terhubung</span>
            <KeyRound className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-white">{providers.length} Model</div>
          <p className="text-[11px] text-emerald-400 font-medium mt-1">
            Konektor API Otomatis Aktif (Zero-Cost Ready)
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Estimasi Biaya</span>
            <Coins className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-emerald-400">
            ${usage?.estimated_total_cost_usd ? usage.estimated_total_cost_usd.toFixed(4) : '0.0000'}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">
            {usage?.total_requests || 0} total respons tersimpan
          </p>
        </div>
      </div>

      {/* Main Sections: Recent Discussions & Providers Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Recent Discussions List */}
        <div className="lg:col-span-2 rounded-2xl bg-slate-900/80 border border-slate-800 p-6 backdrop-blur-md">
          <div className="flex items-center justify-between pb-4 border-b border-slate-800/80 mb-4">
            <h2 className="text-base font-bold text-white">Diskusi Terakhir</h2>
            <button
              onClick={() => navigate('/history')}
              className="text-xs text-emerald-400 hover:text-emerald-300 font-medium transition"
            >
              Lihat Semua Riwayat →
            </button>
          </div>

          {conversations.length === 0 ? (
            <div className="py-12 text-center text-slate-500">
              <MessageSquare className="w-10 h-10 mx-auto mb-2 opacity-40" />
              <p className="text-sm font-medium">Belum ada diskusi yang dimulai</p>
              <button
                onClick={() => navigate('/new-discussion')}
                className="mt-3 px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition"
              >
                Mulai Diskusi Pertama
              </button>
            </div>
          ) : (
            <div className="space-y-2.5">
              {conversations.map((c) => (
                <div
                  key={c.id}
                  onClick={() => navigate(`/history`)}
                  className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 hover:bg-slate-900/80 transition cursor-pointer flex items-center justify-between group"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-semibold uppercase ${
                        c.mode === 'debate'
                          ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                          : c.mode === 'research'
                          ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                          : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                      }`}>
                        {c.mode}
                      </span>
                      <h4 className="font-semibold text-sm text-slate-200 group-hover:text-emerald-300 transition">
                        {c.title}
                      </h4>
                    </div>
                    <p className="text-xs text-slate-500">
                      Dibuat pada: {new Date(c.created_at).toLocaleString('id-ID')}
                    </p>
                  </div>
                  <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-1 transition" />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Council Members Status Panel */}
        <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 backdrop-blur-md flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-4 border-b border-slate-800/80 mb-4">
              <h2 className="text-base font-bold text-white">Anggota Dewan AI</h2>
              <span className="text-xs text-emerald-400 font-semibold flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                Resmi
              </span>
            </div>

            <div className="space-y-3">
              {providers.map((p) => (
                <div
                  key={p.id}
                  className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/80 flex items-center justify-between"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-sm text-slate-200">{p.display_name}</h3>
                      <span className="text-[10px] px-1.5 py-0.5 rounded font-mono bg-slate-800 text-slate-400">
                        {p.selected_model}
                      </span>
                    </div>
                    <p className="text-[11px] text-emerald-400 mt-0.5">
                      {p.api_key_configured ? 'API Key Siap' : 'API Key Belum Diisi'}
                    </p>
                  </div>
                  <a
                    href={p.official_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                    title={`Buka ${p.display_name} resmi`}
                  >
                    <ExternalLink className="w-4 h-4" />
                  </a>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 p-4 rounded-xl bg-emerald-950/30 border border-emerald-500/20 text-xs text-emerald-300">
            <div className="flex items-center gap-2 font-semibold mb-1">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Privasi & Keamanan Terjamin</span>
            </div>
            Data tersimpan lokal di SQLite Mac Anda. Tidak ada scraping antarmuka atau pencurian cookie sesi.
          </div>
        </div>
      </div>
    </div>
  );
};
