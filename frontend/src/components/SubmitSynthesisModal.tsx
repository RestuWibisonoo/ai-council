import React, { useState, useEffect, useRef } from 'react';
import { Copy, Check, ExternalLink, X, Send, Award, AlertCircle } from 'lucide-react';

interface SubmitSynthesisModalProps {
  isOpen: boolean;
  onClose: () => void;
  runId: string;
  synthesisPrompt: string;
  onSubmit: (data: { raw_synthesis: string; moderator_provider?: string }) => Promise<void>;
}

export const SubmitSynthesisModal: React.FC<SubmitSynthesisModalProps> = ({
  isOpen,
  onClose,
  runId,
  synthesisPrompt,
  onSubmit,
}) => {
  const [copied, setCopied] = useState(false);
  const [rawSynthesis, setRawSynthesis] = useState('');
  const [moderatorName, setModeratorName] = useState('Moderator AI Council');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const modalContentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      setCopied(false);
      setError(null);
    }
  }, [isOpen]);

  // Handle ESC
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleCopyPrompt = async () => {
    try {
      await navigator.clipboard.writeText(synthesisPrompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError('Gagal menyalin otomatis. Harap salin teks manual.');
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawSynthesis.trim()) {
      setError('Harap masukkan teks sintesis.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        raw_synthesis: rawSynthesis.trim(),
        moderator_provider: moderatorName.trim() || 'Moderator Dewan',
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Gagal menyimpan sintesis');
    } finally {
      setIsSubmitting(false);
    }
  };

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
      aria-labelledby="synthModalTitle"
    >
      <div
        ref={modalContentRef}
        className="w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]"
      >
        <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center">
              <Award className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <h2 id="synthModalTitle" className="text-base font-bold text-slate-100">
                Sintesis Konsensus Akhir Moderator
              </h2>
              <p className="text-xs text-slate-400">
                Salin seluruh transkrip debat ke AI moderator pilihan Anda, lalu tempelkan sintesis 8 poin di sini.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto space-y-4 flex-1">
          {error && (
            <div className="p-3 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Action Row */}
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleCopyPrompt}
              className={`flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold transition ${
                copied
                  ? 'bg-emerald-600 text-white'
                  : 'bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/40'
              }`}
            >
              {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
              <span>{copied ? 'Prompt Moderator Disalin!' : 'Salin Prompt Moderator Lengkap'}</span>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 pt-1">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1.5">
                Tempelkan Teks Sintesis Moderator (8 Bagian)
              </label>
              <textarea
                value={rawSynthesis}
                onChange={(e) => setRawSynthesis(e.target.value)}
                placeholder="Tempelkan sintesis di sini (1. Ringkasan Masalah, 2. Kesepakatan Antarmodel, 3. Perbedaan Pendapat, 4. Kritik yang Belum Terselesaikan, dst.)..."
                rows={9}
                className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500/50 focus:border-emerald-500 transition resize-y font-sans"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1">
                Nama / Identitas Moderator
              </label>
              <input
                type="text"
                value={moderatorName}
                onChange={(e) => setModeratorName(e.target.value)}
                placeholder="Contoh: Moderator Dewan / Claude 3.7 / GPT-4o Moderator"
                className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-800 text-slate-300 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            <div className="pt-3 border-t border-slate-800 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-slate-400 hover:text-slate-200 text-sm font-medium transition"
              >
                Batal
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !rawSynthesis.trim()}
                className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-semibold transition shadow-lg shadow-emerald-600/20"
              >
                <Send className="w-4 h-4" />
                <span>{isSubmitting ? 'Menyimpan...' : 'Selesaikan & Simpan Konsensus'}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};
