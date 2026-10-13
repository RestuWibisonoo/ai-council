import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Flame, ArrowRight, ShieldAlert, Cpu, Award, CheckCircle } from 'lucide-react';

export const DebatePage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/30 text-xs font-semibold mb-3">
            <Flame className="w-3.5 h-3.5" />
            <span>State Machine AI Debate</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            AI Debate & Cross-Critique Framework
          </h1>
          <p className="text-sm text-slate-400 mt-1 max-w-2xl">
            Sistem perdebatan intelektual multi-putaran antar model AI untuk menguji ketahanan argumen, menelanjangi kesalahan logika, dan menghasilkan sintesis berbasis fakta.
          </p>
        </div>

        <button
          onClick={() => navigate('/new-discussion?mode=debate')}
          className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-sm transition shadow-lg shadow-amber-500/20"
        >
          <Flame className="w-4 h-4 fill-current" />
          <span>Mulai Sesi Debat Baru</span>
        </button>
      </div>

      {/* 4-Stage Flow Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
          <div>
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Tahap 1</span>
            <h3 className="font-bold text-base text-slate-100 mt-1 mb-2">Initial Analysis</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Setiap AI mengambil posisi awal, memaparkan bukti pendukung, dan menjelaskan asumsi yang melandasi pendapatnya.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-emerald-400 font-medium">
            ✔ Independen tanpa saling melihat
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
          <div>
            <span className="text-xs font-bold text-amber-500 uppercase tracking-wider">Tahap 2</span>
            <h3 className="font-bold text-base text-slate-100 mt-1 mb-2">Cross-Critique</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Model saling meninjau argumen lawan untuk menguji klaim tanpa bukti, kontradiksi, bias, dan kesalahan logika formal.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-amber-400 font-medium">
            ✔ Pemeriksaan 7 kriteria kritis
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
          <div>
            <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">Tahap 3</span>
            <h3 className="font-bold text-base text-slate-100 mt-1 mb-2">Rebuttal</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Peserta menanggapi kritik balik: mengakui kekeliruan jika kritik valid, atau menyajikan bukti baru jika tetap bertahan.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-indigo-400 font-medium">
            ✔ Mengakui atau merevisi posisi
          </div>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between">
          <div>
            <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider">Tahap 4</span>
            <h3 className="font-bold text-base text-slate-100 mt-1 mb-2">Final Synthesis</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Moderator menyatukan seluruh jalannya debat menjadi kesimpulan objektif dalam 8 struktur konsensus.
            </p>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] text-cyan-400 font-medium">
            ✔ Ringkasan 8 bagian komprehensif
          </div>
        </div>
      </div>

      {/* Rules & Integrity Box */}
      <div className="p-6 rounded-2xl bg-slate-950/70 border border-slate-800">
        <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-3">
          Prinsip Integritas Moderator Dewan
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-slate-400">
          <div className="flex gap-2.5">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <p>
              <strong className="text-slate-200">Bukan Mayoritas:</strong> Kebenaran ilmiah tidak ditentukan oleh pemungutan suara mayoritas model.
            </p>
          </div>
          <div className="flex gap-2.5">
            <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
            <p>
              <strong className="text-slate-200">Bebas Halusinasi:</strong> Kutipan dan referensi fiktif disaring secara ketat oleh instruksi sistem.
            </p>
          </div>
          <div className="flex gap-2.5">
            <Award className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />
            <p>
              <strong className="text-slate-200">Transparansi Celah:</strong> Hal-hal yang belum terverifikasi dicatat tegas sebagai ketidakpastian.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
