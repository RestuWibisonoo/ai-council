import React, { useState, useEffect, useRef } from 'react';
import { Copy, Check, ExternalLink, X, Send, AlertCircle } from 'lucide-react';
import { ModelResponse } from '../services/api';

interface ManualBridgeModalProps {
  isOpen: boolean;
  onClose: () => void;
  responseItem: ModelResponse | null;
  officialUrl: string;
  providerDisplayName: string;
  onSubmit: (responseId: string, content: string, modelId?: string) => Promise<void>;
}

export const ManualBridgeModal: React.FC<ManualBridgeModalProps> = ({
  isOpen,
  onClose,
  responseItem,
  officialUrl,
  providerDisplayName,
  onSubmit,
}) => {
  const [copied, setCopied] = useState(false);
  const [autoFilling, setAutoFilling] = useState(false);
  const [responseText, setResponseText] = useState('');
  const [modelIdentity, setModelIdentity] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const modalContentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (responseItem) {
      setResponseText(responseItem.content || '');
      setModelIdentity(responseItem.model_id || '');
      setCopied(false);
      setError(null);
    }
  }, [responseItem]);

  // Handle ESC key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !responseItem) return null;

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(responseItem.prompt_used);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      setError('Gagal menyalin otomatis. Silakan blok dan salin teks prompt manual.');
    }
  };

  const handlePlaywrightFill = async () => {
    const rawProvider = (responseItem?.provider || '').toLowerCase();
    const name = providerDisplayName.toLowerCase();
    const provider = rawProvider.includes('gemini') || name.includes('gemini') || name.includes('google')
      ? 'gemini'
      : rawProvider.includes('claude') || name.includes('claude') || name.includes('anthropic')
        ? 'claude'
        : rawProvider.includes('notebook') || name.includes('notebook')
          ? 'notebooklm'
          : rawProvider.includes('chatgpt') || rawProvider.includes('openai') || name.includes('chatgpt') || name.includes('openai')
            ? 'chatgpt'
            : null;
    if (!provider) {
      setError('Provider ini belum didukung oleh Playwright Bridge.');
      return;
    }
    setAutoFilling(true);
    setError(null);
    try {
      const response = await fetch('/api/playwright-bridge/open-fill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, prompt: responseItem?.prompt_used || '' }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || 'Playwright Bridge gagal membuka browser.');
      setCopied(false);
      setError(null);
      window.alert(payload.message || 'Prompt dimasukkan. Periksa browser lalu kirim secara manual.');
    } catch (err: any) {
      setError(err.message || 'Playwright Bridge gagal. Pastikan backend lokal dan Chromium sudah disiapkan.');
    } finally {
      setAutoFilling(false);
    }
  };

  const handleOpenOfficial = () => {
    window.open(officialUrl, '_blank', 'noopener,noreferrer');
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!responseText.trim()) {
      setError('Harap tempelkan respons teks sebelum menyimpan.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit(responseItem.id, responseText.trim(), modelIdentity.trim() || undefined);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Gagal menyimpan respons');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Light dismiss on backdrop click
  const handleBackdropClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (modalContentRef.current && !modalContentRef.current.contains(e.target as Node)) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="bridgeModalTitle"
    >
      <div
        ref={modalContentRef}
        className="w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Mode A — Manual Bridge
              </span>
              <h2 id="bridgeModalTitle" className="text-lg font-bold text-slate-100">
                Konektor {providerDisplayName}
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Salin prompt ke layanan resmi {providerDisplayName}, lalu tempelkan jawabannya kembali ke sini.
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
            aria-label="Tutup modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Action Row */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <button
              type="button"
              onClick={handleCopyPrompt}
              className={`flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium text-sm transition shadow-sm ${
                copied
                  ? 'bg-emerald-600 text-white'
                  : 'bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/40'
              }`}
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              <span>{copied ? 'Prompt Disalin!' : '1. Salin Prompt'}</span>
            </button>

            <button
              type="button"
              onClick={handleOpenOfficial}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium text-sm bg-indigo-600 hover:bg-indigo-500 text-white transition shadow-sm"
            >
              <ExternalLink className="w-4 h-4" />
              <span>2. Buka {providerDisplayName}</span>
            </button>

            <button
              type="button"
              onClick={handlePlaywrightFill}
              disabled={autoFilling}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl font-medium text-sm bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-white transition shadow-sm"
              title="Membuka browser lokal dan mengisi prompt tanpa mengirim otomatis"
            >
              <ExternalLink className="w-4 h-4" />
              <span>{autoFilling ? 'Menyiapkan...' : '3. Isi via Playwright'}</span>
            </button>
          </div>

          {/* Prompt Preview Box */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Teks Prompt yang Dihasilkan
              </label>
              <span className="text-[11px] text-slate-500">
                Tahap: <span className="text-slate-300 font-mono">{responseItem.stage}</span>
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-slate-950/70 border border-slate-800 text-slate-300 text-xs font-mono whitespace-pre-wrap max-h-44 overflow-y-auto leading-relaxed select-all">
              {responseItem.prompt_used}
            </div>
          </div>

          {/* Paste Response Form */}
          <form onSubmit={handleSubmit} className="space-y-4 pt-1">
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  3. Tempel Respons dari {providerDisplayName}
                </label>
                <span className="text-[11px] text-slate-400">
                  {responseText.length} karakter
                </span>
              </div>
              <textarea
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
                placeholder={`Tempelkan hasil jawaban lengkap yang diberikan oleh ${providerDisplayName} di sini...`}
                rows={7}
                className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition resize-y font-sans"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Identitas Model / Catatan Akun (Opsional)
              </label>
              <input
                type="text"
                value={modelIdentity}
                onChange={(e) => setModelIdentity(e.target.value)}
                placeholder="Contoh: ChatGPT Go / Claude 3.5 Free / Gemini Pro Web"
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            {/* Footer Buttons */}
            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 text-sm font-medium transition"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !responseText.trim()}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium transition shadow-lg shadow-emerald-600/20"
              >
                <Send className="w-4 h-4" />
                <span>{isSubmitting ? 'Menyimpan...' : 'Simpan Respons ke Dewan'}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
