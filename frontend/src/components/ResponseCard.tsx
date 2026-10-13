import React, { useState } from 'react';
import {
  Copy,
  Check,
  ExternalLink,
  Edit3,
  Bot,
  AlertTriangle,
  Clock,
  Sparkles,
  Cpu
} from 'lucide-react';
import { ModelResponse } from '../services/api';

interface ResponseCardProps {
  response: ModelResponse;
  officialUrl: string;
  onOpenManualBridge: (response: ModelResponse) => void;
}

export const ResponseCard: React.FC<ResponseCardProps> = ({
  response,
  officialUrl,
  onOpenManualBridge,
}) => {
  const [copied, setCopied] = useState(false);

  const getProviderTheme = (provider: string) => {
    switch (provider.toLowerCase()) {
      case 'chatgpt':
        return {
          name: 'ChatGPT',
          border: 'border-emerald-500/30',
          badge: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
          dot: 'bg-emerald-400',
        };
      case 'claude':
        return {
          name: 'Claude',
          border: 'border-amber-500/30',
          badge: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
          dot: 'bg-amber-400',
        };
      case 'gemini':
        return {
          name: 'Gemini',
          border: 'border-blue-500/30',
          badge: 'bg-blue-500/15 text-blue-300 border-blue-500/30',
          dot: 'bg-blue-400',
        };
      case 'notebooklm':
        return {
          name: 'NotebookLM',
          border: 'border-indigo-500/30',
          badge: 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30',
          dot: 'bg-indigo-400',
        };
      default:
        return {
          name: provider.toUpperCase(),
          border: 'border-slate-700',
          badge: 'bg-slate-800 text-slate-300 border-slate-700',
          dot: 'bg-slate-400',
        };
    }
  };

  const theme = getProviderTheme(response.provider);

  const handleCopyContent = async () => {
    if (!response.content) return;
    try {
      await navigator.clipboard.writeText(response.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  return (
    <div
      className={`rounded-2xl bg-slate-900/80 border ${theme.border} flex flex-col shadow-lg backdrop-blur-md overflow-hidden transition-all hover:border-slate-700`}
    >
      {/* Header */}
      <div className="p-4 border-b border-slate-800/80 bg-slate-950/40 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
            <Bot className="w-4 h-4 text-slate-200" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-sm text-slate-100">{theme.name}</span>
              <span className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${theme.badge}`}>
                {response.integration_mode === 'api' ? 'Official API' : 'Manual Bridge'}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              {response.model_id || 'Model default'}
            </p>
          </div>
        </div>

        {/* Status Indicator */}
        <div>
          {response.status === 'completed' && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
              Selesai
            </span>
          )}
          {response.status === 'pending' && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/15 text-amber-300 border border-amber-500/30 animate-pulse">
              <Clock className="w-3 h-3" />
              Menunggu Respons
            </span>
          )}
          {response.status === 'failed' && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/15 text-rose-300 border border-rose-500/30">
              <AlertTriangle className="w-3 h-3" />
              Gagal
            </span>
          )}
        </div>
      </div>

      {/* Content Area */}
      <div className="p-5 flex-1 min-h-[200px] flex flex-col justify-between">
        {response.status === 'completed' ? (
          <div className="prose prose-invert max-w-none text-slate-200 text-sm leading-relaxed whitespace-pre-wrap font-sans">
            {response.content}
          </div>
        ) : response.status === 'failed' ? (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
            <p className="font-semibold mb-1">Terjadi kesalahan pada provider:</p>
            <p>{response.error_message || 'Gagal memproses respons.'}</p>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center px-4">
            <div className="w-12 h-12 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400 mb-3">
              <Edit3 className="w-6 h-6 text-emerald-400" />
            </div>
            <h4 className="text-sm font-semibold text-slate-200 mb-1">
              Respons Belum Dimasukkan
            </h4>
            <p className="text-xs text-slate-400 max-w-xs mb-4">
              Buka {theme.name} resmi, tempelkan prompt yang telah disiapkan sistem, lalu salin kembali jawabannya.
            </p>
            <button
              onClick={() => onOpenManualBridge(response)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-lg shadow-emerald-600/20"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>Buka Manual Bridge & Salin Prompt</span>
            </button>
          </div>
        )}

        {/* Footer Metrics & Actions */}
        <div className="mt-5 pt-3.5 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-3 text-[11px]">
            {response.total_tokens > 0 && (
              <span className="flex items-center gap-1 text-slate-400">
                <Cpu className="w-3 h-3 text-slate-500" />
                {response.total_tokens} tokens
              </span>
            )}
            {response.estimated_cost_usd > 0 ? (
              <span className="text-amber-400 font-mono">
                ${response.estimated_cost_usd.toFixed(5)}
              </span>
            ) : (
              <span className="text-emerald-400 font-medium">
                Biaya: Rp 0 (Manual)
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {response.status === 'completed' && (
              <button
                onClick={handleCopyContent}
                className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition"
                title="Salin jawaban ini"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            )}
            <button
              onClick={() => onOpenManualBridge(response)}
              className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-medium transition flex items-center gap-1"
            >
              <Edit3 className="w-3 h-3" />
              <span>{response.status === 'completed' ? 'Ubah / Edit' : 'Isi Respons'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
