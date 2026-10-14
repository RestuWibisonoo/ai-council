import React, { useState } from 'react';
import {
  Copy,
  Check,
  Bot,
  AlertTriangle,
  Clock,
  Cpu
} from 'lucide-react';
import { ModelResponse } from '../services/api';

interface ResponseCardProps {
  response: ModelResponse;
  officialUrl?: string;
}

export const ResponseCard: React.FC<ResponseCardProps> = ({
  response,
}) => {
  const [copiedContent, setCopiedContent] = useState(false);

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
      case 'openrouter':
        return {
          name: 'OpenRouter',
          border: 'border-purple-500/30',
          badge: 'bg-purple-500/15 text-purple-300 border-purple-500/30',
          dot: 'bg-purple-400',
        };
      case 'ollama':
        return {
          name: 'Ollama Lokal',
          border: 'border-orange-500/30',
          badge: 'bg-orange-500/15 text-orange-300 border-orange-500/30',
          dot: 'bg-orange-400',
        };
      case 'qwen':
      case 'dashscope':
        return {
          name: 'Qwen / Alibaba',
          border: 'border-cyan-500/30',
          badge: 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30',
          dot: 'bg-cyan-400',
        };
      case 'deepseek':
        return {
          name: 'DeepSeek',
          border: 'border-sky-500/30',
          badge: 'bg-sky-500/15 text-sky-300 border-sky-500/30',
          dot: 'bg-sky-400',
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
      setCopiedContent(true);
      setTimeout(() => setCopiedContent(false), 2000);
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
                {response.integration_mode === 'manual' ? 'Arsip Manual' : 'Official API'}
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
          {response.status === 'in_progress' && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-blue-500/15 text-blue-300 border border-blue-500/30 animate-pulse">
              <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping"></span>
              Sedang Berpikir...
            </span>
          )}
          {response.status === 'pending' && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-800 text-slate-400 border border-slate-700">
              <Clock className="w-3 h-3" />
              Menunggu Giliran
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
        {response.status === 'in_progress' ? (
          <div className="flex flex-col items-center justify-center h-full my-auto py-12 space-y-3">
            <div className="w-8 h-8 rounded-full border-2 border-blue-400 border-t-transparent animate-spin"></div>
            <p className="text-xs text-blue-300 font-semibold">Model AI sedang memproses analisis secara otomatis...</p>
            <p className="text-[11px] text-slate-500">Hasil akan tampil begitu inferensi API selesai.</p>
          </div>
        ) : response.status === 'completed' ? (
          <div className="space-y-3">
            <div className="prose prose-invert max-w-none text-slate-200 text-sm leading-relaxed whitespace-pre-wrap font-sans">
              {response.content}
            </div>
          </div>
        ) : response.status === 'failed' ? (
          <div className="space-y-4 my-auto py-4">
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              <p className="font-semibold mb-1">Terjadi kesalahan pada panggilan API provider:</p>
              <p>{response.error_message || 'Gagal memproses respons otomatis.'}</p>
            </div>
          </div>
        ) : (
          /* Pending / queued state */
          <div className="flex flex-col items-center justify-center h-full my-auto py-10 space-y-2 text-center">
            <div className="w-10 h-10 rounded-xl bg-slate-800/80 flex items-center justify-center text-slate-400">
              <Clock className="w-5 h-5 text-slate-400" />
            </div>
            <p className="text-xs font-medium text-slate-300">Dalam Antrean Pemrosesan API</p>
            <p className="text-[11px] text-slate-500 max-w-xs leading-relaxed">
              Model AI ini akan dipanggil secara otomatis oleh sistem sesuai giliran tahapan debat.
            </p>
          </div>
        )}

        {/* Footer Metrics & Actions */}
        <div className="mt-5 pt-3.5 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-3 text-[11px]">
            {response.total_tokens > 0 && (
              <span className="flex items-center gap-1 text-slate-400">
                <Cpu className="w-3 h-3 text-slate-500" />
                {response.total_tokens.toLocaleString()} tokens
              </span>
            )}
            {response.estimated_cost_usd > 0 ? (
              <span className="text-amber-400 font-mono">
                ${response.estimated_cost_usd.toFixed(5)}
              </span>
            ) : (
              <span className="text-emerald-400 font-medium">
                Biaya: $0.00 (Gratis)
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {response.status === 'completed' && (
              <button
                onClick={handleCopyContent}
                className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition"
                title="Salin jawaban ini"
              >
                {copiedContent ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedContent ? 'Disalin' : 'Salin'}</span>
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
