import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Columns, ArrowRight, Bot, Sparkles, CheckCircle2 } from 'lucide-react';

export const CompareModelsPage: React.FC = () => {
  const navigate = useNavigate();

  const handleStartComparison = (query: string) => {
    navigate(`/new-discussion?mode=parallel`);
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold mb-3">
            <Columns className="w-3.5 h-3.5" />
            <span>Mode Parallel Evaluation</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Komparasi Model AI Berdampingan
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Kirimkan satu pertanyaan yang sama ke ChatGPT, Claude, dan Gemini secara paralel. Amati perbedaan sudut pandang, kedalaman analisis, dan gaya penalaran masing-masing model secara objektif.
          </p>
        </div>

        <button
          onClick={() => navigate('/new-discussion?mode=parallel')}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm transition shadow-lg shadow-emerald-500/20"
        >
          <span>Buat Komparasi Baru</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>

      {/* Feature Highlights Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/15 text-emerald-400 flex items-center justify-center font-bold mb-4">
            01
          </div>
          <h3 className="font-bold text-base text-slate-100 mb-2">Prompt Seragam</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Sistem membuat prompt yang konsisten dan seimbang untuk setiap provider sehingga perbandingan adil tanpa bias framing.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <div className="w-10 h-10 rounded-xl bg-amber-500/15 text-amber-400 flex items-center justify-center font-bold mb-4">
            02
          </div>
          <h3 className="font-bold text-base text-slate-100 mb-2">Manual Bridge Fleksibel</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Gunakan ChatGPT Go, Claude Free, dan Gemini Pro Anda langsung melalui tombol 1-klik tanpa memerlukan biaya langganan API berbayar.
          </p>
        </div>

        <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <div className="w-10 h-10 rounded-xl bg-indigo-500/15 text-indigo-400 flex items-center justify-center font-bold mb-4">
            03
          </div>
          <h3 className="font-bold text-base text-slate-100 mb-2">Konteks Dokumen Sinkron</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Sertakan potongan dokumen PDF dari knowledge engine lokal ke setiap model secara otomatis dengan kutipan nomor halaman.
          </p>
        </div>
      </div>

      {/* Comparison Demo Preview */}
      <div className="p-6 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-4">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
          Contoh Kasus Komparasi Populer
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {[
            'Perbandingan PostgreSQL vs MySQL untuk sistem analitik event-stream',
            'Evaluasi keamanan zero-trust vs perimeter firewall konvensional',
            'Analisis trade-off Rust vs Go untuk microservices latensi rendah',
            'Perbedaan pendekatan penalaran Claude 3.7 vs GPT-4o pada problem solving matematika',
          ].map((topic, i) => (
            <div
              key={i}
              onClick={() => navigate('/new-discussion?mode=parallel')}
              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-emerald-500/50 hover:bg-slate-900 cursor-pointer transition flex items-center justify-between group"
            >
              <span className="text-xs font-medium text-slate-200 group-hover:text-emerald-300 transition">
                {topic}
              </span>
              <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 transition" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
