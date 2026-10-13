import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Download,
  StopCircle,
  FastForward,
  Award,
  BookOpen,
  FileText,
  Clock,
  Sparkles,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import {
  api,
  DiscussionRun,
  ModelResponse,
  ProviderConfig
} from '../services/api';
import { DebateTimeline } from '../components/DebateTimeline';
import { ResponseCard } from '../components/ResponseCard';
import { SynthesisView } from '../components/SynthesisView';
import { ManualBridgeModal } from '../components/ManualBridgeModal';
import { SubmitSynthesisModal } from '../components/SubmitSynthesisModal';

export const DiscussionDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [run, setRun] = useState<DiscussionRun | null>(null);
  const [providers, setProviders] = useState<ProviderConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAdvancing, setIsAdvancing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [activeManualBridgeResp, setActiveManualBridgeResp] = useState<ModelResponse | null>(null);
  const [isSynthesisModalOpen, setIsSynthesisModalOpen] = useState(false);

  const loadRun = async () => {
    if (!id) return;
    try {
      const [runData, provs] = await Promise.all([
        api.getDiscussion(id),
        api.getProviders(),
      ]);
      setRun(runData);
      setProviders(provs);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Gagal memuat sesi diskusi');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRun();
    // Poll updates every 4 seconds if discussion is awaiting input or running
    const interval = setInterval(() => {
      if (run && (run.status === 'awaiting_input' || run.status === 'in_progress')) {
        loadRun();
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [id, run?.status]);

  const handleOpenManualBridge = (resp: ModelResponse) => {
    setActiveManualBridgeResp(resp);
  };

  const handleManualBridgeSubmit = async (
    responseId: string,
    content: string,
    modelId?: string
  ) => {
    if (!id) return;
    await api.submitManualResponse(id, {
      response_id: responseId,
      content,
      model_id: modelId,
      status: 'completed',
    });
    await loadRun();
  };

  const handleAdvanceStage = async () => {
    if (!id) return;
    setIsAdvancing(true);
    try {
      await api.advanceDebateStage(id);
      await loadRun();
    } catch (err: any) {
      alert(err.message || 'Gagal melanjutkan tahapan');
    } finally {
      setIsAdvancing(false);
    }
  };

  const handleStopDiscussion = async () => {
    if (!id) return;
    if (confirm('Apakah Anda yakin ingin menghentikan sesi diskusi ini?')) {
      await api.stopDiscussion(id);
      await loadRun();
    }
  };

  const handleSynthesisSubmit = async (data: {
    raw_synthesis: string;
    moderator_provider?: string;
  }) => {
    if (!id) return;
    await api.submitSynthesis(id, data);
    await loadRun();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[70vh]">
        <div className="flex flex-col items-center gap-3 text-slate-400">
          <RefreshCw className="w-8 h-8 animate-spin text-emerald-400" />
          <p className="text-sm">Memuat sesi diskusi AI Council...</p>
        </div>
      </div>
    );
  }

  if (!run) {
    return (
      <div className="p-8 text-center text-slate-400">
        <AlertCircle className="w-10 h-10 mx-auto text-rose-400 mb-2" />
        <h2 className="text-lg font-bold text-white mb-2">Sesi Tidak Ditemukan</h2>
        <p className="text-sm mb-4">Sesi diskusi yang Anda cari tidak tersedia di database lokal.</p>
        <button
          onClick={() => navigate('/')}
          className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 text-xs font-semibold"
        >
          Kembali ke Dashboard
        </button>
      </div>
    );
  }

  const getProviderConfig = (providerId: string) => {
    return (
      providers.find((p) => p.id === providerId) || {
        official_url: `https://${providerId}.com`,
        display_name: providerId.toUpperCase(),
      }
    );
  };

  const currentStageResponses = run.responses.filter(
    (r) => r.stage === run.current_stage || run.mode === 'parallel'
  );

  const canAdvanceStage =
    run.mode === 'debate' &&
    run.current_stage !== 'completed' &&
    run.status !== 'stopped';

  // Get active synthesis prompt for modal
  const synthesisPlaceholderResp = run.responses.find((r) => r.stage === 'final_synthesis');
  const synthPrompt = synthesisPlaceholderResp?.prompt_used || 'Prompt sintesis moderator...';

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-7">
      {/* Top Navigation & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 hover:bg-slate-800 text-slate-400 hover:text-slate-100 transition"
            title="Kembali"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded text-[11px] font-bold uppercase ${
                run.mode === 'debate'
                  ? 'bg-amber-500/15 text-amber-300 border border-amber-500/30'
                  : run.mode === 'research'
                  ? 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
                  : 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30'
              }`}>
                {run.mode}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                ID: {run.id.slice(0, 8)}
              </span>
            </div>
            <h1 className="text-lg font-bold text-white mt-0.5 line-clamp-1">
              {run.query}
            </h1>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2.5">
          <a
            href={api.getExportUrl(run.id)}
            download
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Ekspor Laporan</span>
          </a>

          {run.status !== 'completed' && run.status !== 'stopped' && (
            <button
              onClick={handleStopDiscussion}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 hover:bg-rose-950/40 text-rose-400 border border-rose-500/30 text-xs font-semibold transition"
            >
              <StopCircle className="w-3.5 h-3.5" />
              <span>Hentikan</span>
            </button>
          )}

          {canAdvanceStage && (
            <button
              onClick={handleAdvanceStage}
              disabled={isAdvancing}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 text-slate-950 font-bold text-xs transition shadow-lg shadow-emerald-500/20"
            >
              <FastForward className="w-4 h-4 fill-current" />
              <span>
                {isAdvancing
                  ? 'Melanjutkan...'
                  : run.current_stage === 'rebuttal'
                  ? 'Lanjut ke Sintesis Moderator'
                  : 'Lanjut ke Tahap Berikutnya'}
              </span>
            </button>
          )}

          {run.current_stage === 'final_synthesis' && run.status !== 'completed' && (
            <button
              onClick={() => setIsSynthesisModalOpen(true)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition shadow-lg shadow-indigo-600/20"
            >
              <Award className="w-4 h-4" />
              <span>Isi Sintesis Konsensus</span>
            </button>
          )}
        </div>
      </div>

      {/* Debate Timeline (If in Debate Mode) */}
      {run.mode === 'debate' && (
        <DebateTimeline
          currentStage={run.current_stage}
          currentRound={run.current_round}
          maxRounds={run.max_rounds}
        />
      )}

      {/* Verified Document References Card (If any) */}
      {run.source_references && run.source_references.length > 0 && (
        <div className="p-4 rounded-2xl bg-indigo-950/30 border border-indigo-500/30 text-xs">
          <div className="flex items-center gap-2 font-bold text-indigo-300 uppercase tracking-wider mb-2">
            <BookOpen className="w-4 h-4 text-indigo-400" />
            <span>Kutipan Dokumen Terverifikasi yang Disertakan ke Prompt</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-2">
            {run.source_references.map((ref, idx) => (
              <div key={idx} className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-slate-300">
                <span className="font-semibold text-indigo-400 mr-1.5">[Halaman {ref.page_number}]:</span>
                <span className="italic font-serif">"{ref.quote}"</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Model Responses Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
            Respons Dewan AI ({run.current_stage.replace('_', ' ')})
          </h3>
          <span className="text-xs text-slate-400">
            {currentStageResponses.filter((r) => r.status === 'completed').length} dari{' '}
            {currentStageResponses.length} respons selesai
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {currentStageResponses.map((resp) => {
            const provCfg = getProviderConfig(resp.provider);
            return (
              <ResponseCard
                key={resp.id}
                response={resp}
                officialUrl={provCfg.official_url}
                onOpenManualBridge={handleOpenManualBridge}
              />
            );
          })}
        </div>
      </div>

      {/* Final Moderator Synthesis Section */}
      {(run.syntheses && run.syntheses.length > 0) || run.current_stage === 'final_synthesis' ? (
        <div className="pt-4">
          <SynthesisView
            synthesis={run.syntheses && run.syntheses.length > 0 ? run.syntheses[0] : null}
            onOpenSubmitModal={() => setIsSynthesisModalOpen(true)}
          />
        </div>
      ) : null}

      {/* Manual Bridge Modal */}
      {activeManualBridgeResp && (
        <ManualBridgeModal
          isOpen={Boolean(activeManualBridgeResp)}
          onClose={() => setActiveManualBridgeResp(null)}
          responseItem={activeManualBridgeResp}
          officialUrl={getProviderConfig(activeManualBridgeResp.provider).official_url}
          providerDisplayName={getProviderConfig(activeManualBridgeResp.provider).display_name}
          onSubmit={handleManualBridgeSubmit}
        />
      )}

      {/* Submit Synthesis Modal */}
      <SubmitSynthesisModal
        isOpen={isSynthesisModalOpen}
        onClose={() => setIsSynthesisModalOpen(false)}
        runId={run.id}
        synthesisPrompt={synthPrompt}
        onSubmit={handleSynthesisSubmit}
      />
    </div>
  );
};
