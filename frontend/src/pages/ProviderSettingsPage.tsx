import React, { useState, useEffect } from 'react';
import {
  KeyRound,
  ShieldCheck,
  CheckCircle,
  AlertTriangle,
  Play,
  ExternalLink,
  Bot,
  DollarSign,
  Cpu,
  Save,
  Check
} from 'lucide-react';
import { api, ProviderConfig } from '../services/api';

export const ProviderSettingsPage: React.FC = () => {
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [loading, setLoading] = useState(true);

  // Form states per provider
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [selectedModels, setSelectedModels] = useState<Record<string, string>>({});
  const [modes, setModes] = useState<Record<string, 'manual' | 'api'>>({});
  const [limits, setLimits] = useState<Record<string, number>>({});
  const [testResults, setTestResults] = useState<Record<string, { success: boolean; msg: string }>>({});
  const [testingId, setTestingId] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<Record<string, boolean>>({});

  const loadProviders = async () => {
    try {
      const data = await api.getProviders();
      setProviders(data);
      const modMap: Record<string, string> = {};
      const modeMap: Record<string, 'manual' | 'api'> = {};
      const limMap: Record<string, number> = {};
      data.forEach((p) => {
        modMap[p.id] = p.selected_model;
        modeMap[p.id] = p.default_mode;
        limMap[p.id] = p.usage_limit_monthly_usd;
      });
      setSelectedModels(modMap);
      setModes(modeMap);
      setLimits(limMap);
    } catch (err) {
      console.error('Failed to load providers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProviders();
  }, []);

  const handleSave = async (providerId: string) => {
    const key = apiKeys[providerId];
    const mode = modes[providerId];
    const model = selectedModels[providerId];
    const limit = limits[providerId];

    try {
      await api.updateProvider(providerId, {
        default_mode: mode,
        selected_model: model,
        usage_limit_monthly_usd: limit,
        ...(key ? { api_key: key } : {}),
      });
      setSaveSuccess((prev) => ({ ...prev, [providerId]: true }));
      setTimeout(() => {
        setSaveSuccess((prev) => ({ ...prev, [providerId]: false }));
      }, 2500);
      await loadProviders();
    } catch (err: any) {
      alert(err.message || 'Gagal menyimpan pengaturan provider');
    }
  };

  const handleTestConnection = async (providerId: string) => {
    setTestingId(providerId);
    setTestResults((prev) => ({ ...prev, [providerId]: { success: false, msg: 'Menguji koneksi...' } }));
    try {
      const res = await api.testProvider(providerId, {
        api_key: apiKeys[providerId] || undefined,
        model: selectedModels[providerId],
      });
      setTestResults((prev) => ({
        ...prev,
        [providerId]: { success: res.success, msg: res.message },
      }));
    } catch (err: any) {
      setTestResults((prev) => ({
        ...prev,
        [providerId]: { success: false, msg: err.message || 'Gagal menguji provider' },
      }));
    } finally {
      setTestingId(null);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-400">Memuat konfigurasi provider...</div>;
  }

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-7">
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 text-xs font-semibold mb-2">
            <KeyRound className="w-3.5 h-3.5" />
            <span>Integrasi Multi-Model</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Pengaturan Provider AI Dewan
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Konfigurasi konektor ChatGPT, Claude, Gemini, dan NotebookLM. Tanpa API key berbayar, Anda tetap dapat menggunakan 100% fitur via Mode Manual Bridge.
          </p>
        </div>
      </div>

      {/* Notice Banner */}
      <div className="p-4 rounded-2xl bg-slate-900/80 border border-emerald-500/30 text-xs text-slate-300 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div>
          <h4 className="font-bold text-emerald-300 text-sm mb-0.5">
            Keamanan Kredensial Terjamin
          </h4>
          <p className="leading-relaxed text-slate-400">
            API key hanya diproses di backend dan tidak pernah dikirim ke frontend atau disimpan dalam repositori kode. Kunci tersimpan di lingkungan lokal privat yang aman.
          </p>
        </div>
      </div>

      {/* Provider Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {providers.map((p) => {
          const testRes = testResults[p.id];
          const isSaved = saveSuccess[p.id];

          return (
            <div
              key={p.id}
              className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md flex flex-col justify-between space-y-5"
            >
              {/* Header */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-slate-200" />
                    </div>
                    <div>
                      <h3 className="font-bold text-base text-white">{p.display_name}</h3>
                      <a
                        href={p.official_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[11px] text-emerald-400 hover:underline flex items-center gap-1"
                      >
                        <span>{p.official_url}</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>

                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-semibold border ${
                      p.api_key_configured
                        ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30'
                        : 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                    }`}
                  >
                    {p.api_key_configured ? 'API Siap' : 'Mode Manual'}
                  </span>
                </div>

                {/* Mode Selector Radio */}
                <div className="mt-4 pt-3 border-t border-slate-800 space-y-3">
                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                      Mode Operasi
                    </label>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        type="button"
                        onClick={() => setModes((prev) => ({ ...prev, [p.id]: 'manual' }))}
                        className={`py-2 px-3 rounded-xl text-xs font-bold border transition ${
                          modes[p.id] === 'manual'
                            ? 'bg-emerald-500/15 border-emerald-500 text-emerald-300'
                            : 'bg-slate-950 border-slate-800 text-slate-400'
                        }`}
                      >
                        Mode A: Manual Bridge
                      </button>
                      <button
                        type="button"
                        onClick={() => setModes((prev) => ({ ...prev, [p.id]: 'api' }))}
                        className={`py-2 px-3 rounded-xl text-xs font-bold border transition ${
                          modes[p.id] === 'api'
                            ? 'bg-indigo-500/15 border-indigo-500 text-indigo-300'
                            : 'bg-slate-950 border-slate-800 text-slate-400'
                        }`}
                      >
                        Mode B: Official API
                      </button>
                    </div>
                  </div>

                  {/* Model Choice */}
                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1.5">
                      Pilihan Model
                    </label>
                    <select
                      value={selectedModels[p.id] || p.selected_model}
                      onChange={(e) =>
                        setSelectedModels((prev) => ({ ...prev, [p.id]: e.target.value }))
                      }
                      className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
                    >
                      {p.supported_models.map((m) => (
                        <option key={m} value={m}>
                          {m}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* API Key Input (Only if not notebooklm) */}
                  {p.id !== 'notebooklm' && (
                    <div>
                      <div className="flex items-center justify-between mb-1">
                        <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                          API Key (Opsional)
                        </label>
                        <span className="text-[10px] text-slate-500">
                          {p.api_key_configured ? '● Terkonfigurasi di server' : 'Belum diisi'}
                        </span>
                      </div>
                      <input
                        type="password"
                        value={apiKeys[p.id] || ''}
                        onChange={(e) =>
                          setApiKeys((prev) => ({ ...prev, [p.id]: e.target.value }))
                        }
                        placeholder={
                          p.api_key_configured
                            ? '•••••••••••••••• (Kunci tersimpan aman)'
                            : 'Masukkan API key jika ingin mode otomatis...'
                        }
                        className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500 font-mono"
                      />
                    </div>
                  )}

                  {/* Monthly Usage Limit */}
                  <div>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">
                      Batas Penggunaan Bulanan (USD)
                    </label>
                    <div className="relative">
                      <span className="absolute left-3 top-2 text-slate-500 text-xs">$</span>
                      <input
                        type="number"
                        step="1"
                        min="0"
                        value={limits[p.id] ?? p.usage_limit_monthly_usd}
                        onChange={(e) =>
                          setLimits((prev) => ({
                            ...prev,
                            [p.id]: parseFloat(e.target.value) || 0,
                          }))
                        }
                        className="w-full pl-7 pr-3 py-1.5 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-xs focus:outline-none focus:ring-1 focus:ring-emerald-500"
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Test Result Message */}
              {testRes && (
                <div
                  className={`p-3 rounded-xl border text-xs ${
                    testRes.success
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                      : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                  }`}
                >
                  <p className="font-semibold mb-0.5">{testRes.success ? 'Koneksi Berhasil' : 'Info Koneksi'}</p>
                  <p>{testRes.msg}</p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 border-t border-slate-800 flex items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => handleTestConnection(p.id)}
                  disabled={testingId === p.id}
                  className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition"
                >
                  {testingId === p.id ? 'Menguji...' : 'Uji Koneksi'}
                </button>

                <button
                  type="button"
                  onClick={() => handleSave(p.id)}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold transition ${
                    isSaved
                      ? 'bg-emerald-600 text-white'
                      : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-md shadow-emerald-500/20'
                  }`}
                >
                  {isSaved ? <Check className="w-3.5 h-3.5" /> : <Save className="w-3.5 h-3.5" />}
                  <span>{isSaved ? 'Tersimpan!' : 'Simpan Pengaturan'}</span>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
