import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  History,
  Search,
  MessageSquare,
  ArrowRight,
  Trash2,
  Calendar,
  ExternalLink
} from 'lucide-react';
import { api, ConversationItem } from '../services/api';

export const ConversationHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFilter, setSelectedFilter] = useState<'all' | 'parallel' | 'debate' | 'research'>('all');
  const [isLoading, setIsLoading] = useState(true);

  const loadConversations = async () => {
    try {
      const data = await api.getConversations();
      setConversations(data);
    } catch (err) {
      console.error('Failed to load conversations:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadConversations();
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (confirm('Hapus sesi percakapan ini beserta seluruh jalannya diskusi?')) {
      await api.deleteConversation(id);
      setConversations(conversations.filter((c) => c.id !== id));
    }
  };

  const handleOpenConversation = async (convId: string) => {
    try {
      // Get conversation details to retrieve run ID
      const res = await fetch(`/api/conversations/${convId}`);
      const data = await res.json();
      if (data.runs && data.runs.length > 0) {
        navigate(`/discussions/${data.runs[0].id}`);
      } else {
        alert('Tidak ada sesi diskusi aktif dalam percakapan ini.');
      }
    } catch {
      alert('Gagal membuka sesi');
    }
  };

  const filtered = conversations.filter((c) => {
    const matchesSearch = c.title.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = selectedFilter === 'all' || c.mode === selectedFilter;
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-7">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold mb-2">
            <History className="w-3.5 h-3.5" />
            <span>Arsip Diskusi</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Riwayat Percakapan & Sesi Dewan
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Daftar seluruh sesi tanya-jawab, debat, dan proyek riset yang tersimpan di database lokal.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="relative flex-1 min-w-[280px]">
          <Search className="w-4 h-4 absolute left-3.5 top-3.5 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Cari topik atau judul diskusi..."
            className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 placeholder-slate-500 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
          />
        </div>

        <div className="flex items-center gap-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800 text-xs">
          {(['all', 'parallel', 'debate', 'research'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setSelectedFilter(mode)}
              className={`px-3 py-1.5 rounded-lg font-semibold capitalize transition ${
                selectedFilter === mode
                  ? 'bg-emerald-500 text-slate-950 shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {mode === 'all' ? 'Semua' : mode}
            </button>
          ))}
        </div>
      </div>

      {/* Table / List */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 overflow-hidden backdrop-blur-md">
        {isLoading ? (
          <div className="p-12 text-center text-slate-400">Memuat riwayat...</div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-500">
            <MessageSquare className="w-10 h-10 mx-auto mb-2 opacity-40" />
            <p className="text-sm font-medium">Tidak ada percakapan yang cocok</p>
          </div>
        ) : (
          <div className="divide-y divide-slate-800/80">
            {filtered.map((c) => (
              <div
                key={c.id}
                onClick={() => handleOpenConversation(c.id)}
                className="p-4 flex items-center justify-between hover:bg-slate-850 hover:bg-slate-900/90 transition cursor-pointer group"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase ${
                      c.mode === 'debate'
                        ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                        : c.mode === 'research'
                        ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                        : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
                    }`}>
                      {c.mode}
                    </span>
                    <h3 className="font-semibold text-sm text-slate-200 group-hover:text-emerald-300 transition">
                      {c.title}
                    </h3>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-slate-500">
                    <span className="flex items-center gap-1">
                      <Calendar className="w-3.5 h-3.5" />
                      {new Date(c.created_at).toLocaleString('id-ID')}
                    </span>
                    <span className="font-mono text-[10px]">ID: {c.id.slice(0, 8)}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={(e) => handleDelete(c.id, e)}
                    className="p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition"
                    title="Hapus percakapan"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                  <div className="p-2 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-1 transition">
                    <ArrowRight className="w-4 h-4" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
