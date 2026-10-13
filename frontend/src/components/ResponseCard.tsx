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
  Cpu,
  ChevronDown,
  ChevronUp
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
  const [copiedContent, setCopiedContent] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState(false);
  const [isAutoFilling, setIsAutoFilling] = useState(false);
  const [showPromptPreview, setShowPromptPreview] = useState(false);

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
      setCopiedContent(true);
      setTimeout(() => setCopiedContent(false), 2000);
    } catch {}
  };

  const handleCopyPrompt = async () => {
    if (!response.prompt_used) return;
    try {
      await navigator.clipboard.writeText(response.prompt_used);
      setCopiedPrompt(true);
      setTimeout(() => setCopiedPrompt(false), 2000);
    } catch {}
  };

  const handleOpenOfficial = () => {
    window.open(officialUrl, '_blank', 'noopener,noreferrer');
  };

  const handlePlaywrightFill = async () => {
    const rawProvider = (response.provider || '').toLowerCase();
    const provider = rawProvider.includes('gemini') || rawProvider.includes('google')
      ? 'gemini'
      : rawProvider.includes('claude') || rawProvider.includes('anthropic')
        ? 'claude'
        : rawProvider.includes('notebook')
          ? 'notebooklm'
          : rawProvider.includes('chatgpt') || rawProvider.includes('openai')
            ? 'chatgpt'
            : null;
    if (!provider) {
      alert('Provider ini belum didukung oleh Playwright Bridge.');
      return;
    }
    setIsAutoFilling(true);
    try {
      const res = await fetch('/api/playwright-bridge/open-fill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, prompt: response.prompt_used || '' }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || 'Playwright Bridge gagal membuka browser.');
      alert(data.message || 'Prompt dimasukkan. Periksa browser lalu kirim secara manual.');
    } catch (err: any) {
      alert(err.message || 'Playwright Bridge gagal. Pastikan backend lokal dan browser sudah siap.');
    } finally {
      setIsAutoFilling(false);
    }
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
      <div className="p-5 flex-1 min-h-[220px] flex flex-col justify-between">
        {response.status === 'completed' ? (
          <div className="space-y-3">
            <div className="prose prose-invert max-w-none text-slate-200 text-sm leading-relaxed whitespace-pre-wrap font-sans">
              {response.content}
            </div>
          </div>
        ) : response.status === 'failed' ? (
          <div className="space-y-4 my-auto py-4">
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              <p className="font-semibold mb-1">Terjadi kesalahan pada provider:</p>
              <p>{response.error_message || 'Gagal memproses respons.'}</p>
            </div>
            <button
              onClick={() => onOpenManualBridge(response)}
              className="w-full py-2.5 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 transition border border-slate-700"
            >
              Coba Isi Ulang Manual
            </button>
          </div>
        ) : (
          /* Pending / Awaiting input state */
          <div className="flex flex-col justify-between h-full space-y-4 py-2">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-amber-300/90 uppercase tracking-wider flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" />
                  Menunggu Jawaban
                </span>
                <button
                  type="button"
                  onClick={() => setShowPromptPreview(!showPromptPreview)}
                  className="text-[11px] text-slate-400 hover:text-slate-200 flex items-center gap-1"
                >
                  <span>{showPromptPreview ? 'Sembunyikan Prompt' : 'Lihat Teks Prompt'}</span>
                  {showPromptPreview ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                </button>
              </div>

              {showPromptPreview && (
                <div className="p-3 mb-3 rounded-xl bg-slate-950/80 border border-slate-800 text-slate-300 text-[11px] font-mono whitespace-pre-wrap max-h-36 overflow-y-auto leading-relaxed select-all">
                  {response.prompt_used}
                </div>
              )}

              <p className="text-xs text-slate-400 leading-relaxed mb-4">
                Prompt telah disiapkan. Salin prompt, tempelkan ke {theme.name} resmi atau gunakan Playwright bridge, lalu tempel jawabannya ke sini.
              </p>

              {/* 3 Quick Step Action Buttons */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 mb-3">
                <button
                  type="button"
                  onClick={handleCopyPrompt}
                  className={`flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium transition border ${
                    copiedPrompt
                      ? 'bg-emerald-600 text-white border-emerald-500'
                      : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
                  }`}
                  title="Salin teks prompt ke clipboard"
                >
                  {copiedPrompt ? <Check className="w-3.5 h-3.5 text-white" /> : <Copy className="w-3.5 h-3.5" />}
                  <span>{copiedPrompt ? 'Disalin!' : '1. Salin'}</span>
                </button>

                <button
                  type="button"
                  onClick={handleOpenOfficial}
                  className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition"
                  title={`Buka situs resmi ${theme.name}`}
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>2. Buka Web</span>
                </button>

                <button
                  type="button"
                  onClick={handlePlaywrightFill}
                  disabled={isAutoFilling}
                  className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium bg-violet-600/30 hover:bg-violet-600/40 text-violet-300 border border-violet-500/40 transition disabled:opacity-50"
                  title="Isi prompt ke browser Playwright tanpa kirim otomatis"
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{isAutoFilling ? 'Proses...' : '3. Playwright'}</span>
                </button>
              </div>

              {/* Main Submit Button */}
              <button
                type="button"
                onClick={() => onOpenManualBridge(response)}
                className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-md shadow-emerald-600/20"
              >
                <Edit3 className="w-4 h-4" />
                <span>4. Tempel & Simpan Respons</span>
              </button>
            </div>
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
                {copiedContent ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
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
