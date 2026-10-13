import React, { useState, useEffect } from 'react';
import {
  Coins,
  Cpu,
  Receipt,
  ShieldCheck,
  TrendingUp,
  Clock,
  CheckCircle,
  HelpCircle
} from 'lucide-react';
import { api, UsageSummary } from '../services/api';

export const UsageCostPage: React.FC = () => {
  const [summary, setSummary] = useState<UsageSummary | null>(null);
  const [records, setRecords] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [sum, recs] = await Promise.all([
          api.getUsageSummary(),
          api.getUsageRecords(50),
        ]);
        setSummary(sum);
        setRecords(recs);
      } catch (err) {
        console.error('Failed to load usage data:', err);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  if (loading) {
    return <div className="p-8 text-center text-slate-400">Memuat laporan biaya & penggunaan...</div>;
  }

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-7">
      <div className="pb-4 border-b border-slate-800">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 text-xs font-semibold mb-2">
          <Coins className="w-3.5 h-3.5" />
          <span>Transparansi Biaya & Token</span>
        </div>
        <h1 className="text-2xl font-black text-white tracking-tight">
          Laporan Penggunaan & Estimasi Biaya
        </h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Audit transparansi yang memisahkan penggunaan tanpa biaya (Manual Bridge) dan panggilan API berbayar.
        </p>
      </div>

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Total Permintaan
          </span>
          <div className="text-2xl font-bold text-white">{summary?.total_requests || 0}</div>
          <p className="text-[11px] text-slate-500 mt-1">Seluruh putaran diskusi</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-emerald-500/30 backdrop-blur-md">
          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider block mb-1">
            Penggunaan Manual (Rp 0)
          </span>
          <div className="text-2xl font-bold text-emerald-300">{summary?.manual_requests || 0}</div>
          <p className="text-[11px] text-emerald-500 font-medium mt-1">
            100% Bebas Biaya API
          </p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-indigo-500/30 backdrop-blur-md">
          <span className="text-xs font-semibold text-indigo-400 uppercase tracking-wider block mb-1">
            Panggilan Official API
          </span>
          <div className="text-2xl font-bold text-indigo-300">{summary?.api_requests || 0}</div>
          <p className="text-[11px] text-slate-500 mt-1">Menggunakan kunci API Anda</p>
        </div>

        <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block mb-1">
            Estimasi Total Biaya
          </span>
          <div className="text-2xl font-bold text-amber-400">
            ${summary?.estimated_total_cost_usd ? summary.estimated_total_cost_usd.toFixed(4) : '0.0000'}
          </div>
          <p className="text-[11px] text-slate-500 mt-1">Berdasarkan tarif resmi provider</p>
        </div>
      </div>

      {/* Provider Breakdown Table */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 backdrop-blur-md">
        <h2 className="text-base font-bold text-white mb-4">
          Rincian Penggunaan per Provider
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="pb-3 font-semibold uppercase">Provider</th>
                <th className="pb-3 font-semibold uppercase">Mode Aktif</th>
                <th className="pb-3 font-semibold uppercase">Jumlah Panggilan</th>
                <th className="pb-3 font-semibold uppercase">Token Tercatat</th>
                <th className="pb-3 font-semibold uppercase">Estimasi Biaya</th>
                <th className="pb-3 font-semibold uppercase">Batas Bulanan</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-200">
              {summary &&
                Object.entries(summary.by_provider).map(([pid, p]) => (
                  <tr key={pid} className="hover:bg-slate-800/40">
                    <td className="py-3 font-bold">{p.display_name}</td>
                    <td className="py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                          p.default_mode === 'api'
                            ? 'bg-indigo-500/20 text-indigo-300'
                            : 'bg-emerald-500/20 text-emerald-300'
                        }`}
                      >
                        {p.default_mode === 'api' ? 'Official API' : 'Manual Bridge'}
                      </span>
                    </td>
                    <td className="py-3 font-mono">{p.requests_count}</td>
                    <td className="py-3 font-mono">{p.tokens.toLocaleString()} tokens</td>
                    <td className="py-3 font-mono text-amber-400">
                      ${p.estimated_cost_usd.toFixed(4)}
                    </td>
                    <td className="py-3 font-mono text-slate-400">
                      ${p.monthly_limit_usd.toFixed(2)}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Recent Request Records Log */}
      <div className="rounded-2xl bg-slate-900/80 border border-slate-800 p-6 backdrop-blur-md">
        <h2 className="text-base font-bold text-white mb-4">
          Log Aktivitas Terakhir
        </h2>
        {records.length === 0 ? (
          <p className="text-xs text-slate-500">Belum ada aktivitas yang dicatat.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="pb-2.5 font-semibold">Waktu</th>
                  <th className="pb-2.5 font-semibold">Provider</th>
                  <th className="pb-2.5 font-semibold">Mode</th>
                  <th className="pb-2.5 font-semibold">Aksi / Tahap</th>
                  <th className="pb-2.5 font-semibold">Token</th>
                  <th className="pb-2.5 font-semibold">Biaya</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {records.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-800/30">
                    <td className="py-2.5 text-slate-500 font-mono text-[11px]">
                      {new Date(r.created_at).toLocaleTimeString('id-ID')}
                    </td>
                    <td className="py-2.5 font-semibold">{r.provider.toUpperCase()}</td>
                    <td className="py-2.5">
                      <span className="capitalize">{r.mode}</span>
                    </td>
                    <td className="py-2.5 font-mono text-slate-400">{r.action}</td>
                    <td className="py-2.5 font-mono">{r.total_tokens}</td>
                    <td className="py-2.5 font-mono text-slate-300">
                      {r.mode === 'manual' ? 'Rp 0' : `$${r.estimated_cost_usd.toFixed(5)}`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
