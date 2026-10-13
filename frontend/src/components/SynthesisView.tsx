import React, { useState } from 'react';
import { Award, CheckCircle, AlertCircle, Bookmark, Compass, HelpCircle, FileCheck, Copy, Check } from 'lucide-react';
import { Synthesis } from '../services/api';

interface SynthesisViewProps {
  synthesis: Synthesis | null;
  onOpenSubmitModal?: () => void;
}

export const SynthesisView: React.FC<SynthesisViewProps> = ({ synthesis, onOpenSubmitModal }) => {
  const [copied, setCopied] = useState(false);

  if (!synthesis) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/40 p-8 text-center flex flex-col items-center justify-center">
        <Award className="w-12 h-12 text-slate-500 mb-3" />
        <h3 className="text-base font-bold text-slate-200 mb-1">
          Sintesis Konsensus Belum Dibuat
        </h3>
        <p className="text-xs text-slate-400 max-w-md mb-4">
          Setelah semua model memberikan argumen, kritik silang, dan sanggahan, moderator akan merangkum konsensus 8 poin ini.
        </p>
        {onOpenSubmitModal && (
          <button
            onClick={onOpenSubmitModal}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition shadow-lg shadow-emerald-600/20"
          >
            Tulis / Tempel Sintesis Moderator
          </button>
        )}
      </div>
    );
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(synthesis.raw_synthesis);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const sections = [
    { title: '1. Ringkasan Masalah', content: synthesis.problem_summary, icon: Bookmark, color: 'text-indigo-400' },
    { title: '2. Kesepakatan Antarmodel', content: synthesis.consensus_points, icon: CheckCircle, color: 'text-emerald-400' },
    { title: '3. Perbedaan Pendapat & Divergensi', content: synthesis.disagreements, icon: AlertCircle, color: 'text-amber-400' },
    { title: '4. Kritik yang Belum Terselesaikan', content: synthesis.unresolved_critiques, icon: HelpCircle, color: 'text-rose-400' },
    { title: '5. Bukti yang Mendukung Kesimpulan', content: synthesis.evidence_backed_claims, icon: FileCheck, color: 'text-cyan-400' },
    { title: '6. Rekomendasi Terpilih', content: synthesis.recommendations, icon: Compass, color: 'text-emerald-300' },
    { title: '7. Ketidakpastian & Kebutuhan Verifikasi', content: synthesis.uncertainties_and_verifications, icon: HelpCircle, color: 'text-yellow-400' },
    { title: '8. Referensi Sumber yang Tersedia', content: synthesis.references_cited, icon: Bookmark, color: 'text-purple-400' },
  ];

  const hasParsedSections = sections.some((s) => Boolean(s.content));

  return (
    <div className="rounded-2xl bg-gradient-to-b from-slate-900 to-slate-950 border border-emerald-500/30 p-6 shadow-2xl relative overflow-hidden">
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-center justify-between pb-4 mb-5 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
            <Award className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              Sintesis Akhir AI Council
              <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                Moderator Terverifikasi
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Evaluasi konsensus komprehensif tanpa asumsi bias mayoritas
            </p>
          </div>
        </div>

        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          <span>{copied ? 'Tersalin' : 'Salin Sintesis'}</span>
        </button>
      </div>

      {/* 8 Structured Points or Raw Synthesis */}
      {hasParsedSections ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {sections.map((sec, idx) => {
            if (!sec.content) return null;
            const Icon = sec.icon;
            return (
              <div
                key={idx}
                className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition"
              >
                <div className="flex items-center gap-2 mb-2">
                  <Icon className={`w-4 h-4 ${sec.color}`} />
                  <h4 className="text-xs font-bold text-slate-200 tracking-wide uppercase">
                    {sec.title}
                  </h4>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                  {sec.content}
                </p>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="prose prose-invert max-w-none text-slate-200 text-sm leading-relaxed whitespace-pre-wrap bg-slate-950/60 p-5 rounded-xl border border-slate-800/80">
          {synthesis.raw_synthesis}
        </div>
      )}
    </div>
  );
};
