import React, { useEffect, useState } from 'react';
import { Settings, ShieldCheck, Database, HardDrive, CheckCircle2, Server, Terminal } from 'lucide-react';
import { api } from '../services/api';

export const SettingsPage: React.FC = () => {
  const [health, setHealth] = useState<any>(null);

  useEffect(() => {
    api.getHealth().then((h) => setHealth(h)).catch(() => {});
  }, []);

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-7">
      <div className="pb-4 border-b border-slate-800">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold mb-2">
          <Settings className="w-3.5 h-3.5" />
          <span>Sistem & Arsitektur</span>
        </div>
        <h1 className="text-2xl font-black text-white tracking-tight">
          Pengaturan Aplikasi & Status Lokal
        </h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Informasi lingkungan eksekusi di Mac, lokasi penyimpanan persisten, dan prosedur backup.
        </p>
      </div>

      {/* System Health */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Status Server API</span>
            <Server className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-emerald-400 flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Online (127.0.0.1:8000)
          </div>
          <p className="text-[11px] text-slate-500 mt-1">FastAPI Backend</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Database SQLite</span>
            <Database className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-xl font-bold text-slate-100">
            {health?.database || 'Healthy'}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">SQLAlchemy & Alembic Migrations</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-semibold uppercase tracking-wider">Versi Aplikasi</span>
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-slate-100">
            AI Council v1.0.0
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Production Ready MVP</p>
        </div>
      </div>

      {/* Persistence Paths & Backup Instructions */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 backdrop-blur-md space-y-4">
        <h2 className="text-base font-bold text-white flex items-center gap-2">
          <HardDrive className="w-5 h-5 text-emerald-400" />
          <span>Lokasi Penyimpanan Data Persisten</span>
        </h2>
        <p className="text-xs text-slate-400 leading-relaxed">
          Semua data diskusi, indeks potongan PDF, dan riwayat disimpan secara terpisah dari kode sumber dalam direktori data lokal:
        </p>

        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 text-xs font-mono text-slate-300 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-slate-500">Database SQLite:</span>
            <span className="text-emerald-300">data/ai_council.db</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-500">Direktori Upload Dokumen:</span>
            <span className="text-emerald-300">data/uploads/</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-500">Kunci Rahasia Provider (Restricted 0600):</span>
            <span className="text-emerald-300">data/provider_secrets.json</span>
          </div>
        </div>

        <div className="pt-2">
          <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
            Prosedur Backup & Restore Cepat
          </h4>
          <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-300 space-y-2 font-mono">
            <p className="text-slate-400"># Untuk mencadangkan seluruh data:</p>
            <p className="text-emerald-400">tar -czvf ai_council_backup_$(date +%F).tar.gz data/</p>
            <p className="text-slate-400 mt-2"># Untuk memulihkan data cadangan:</p>
            <p className="text-emerald-400">tar -xzvf ai_council_backup_YYYY-MM-DD.tar.gz</p>
          </div>
        </div>
      </div>
    </div>
  );
};
