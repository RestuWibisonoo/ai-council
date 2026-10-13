import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Download,
  StopCircle,
  Play,
  FastForward,
  Award,
  BookOpen,
  FileText,
  Clock,
  Sparkles,
  RefreshCw,
  AlertCircle,
  Flame
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
  const [isContinuingToDebate, setIsContinuingToDebate] = useState(false);
  const [selectedStageTab, setSelectedStageTab] = useState<string>('all');
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [activeManualBridgeResp, setActiveManualBridgeResp] = useState<ModelResponse | null>(null);
  const [isSynthesisModalOpen, setIsSynthesisModalOpen] = useState(false);
  const [isPartialSynthesis, setIsPartialSynthesis] = useState(false);

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
    try {
      await api.submitManualResponse(id, {
        response_id: responseId,
        content,
        model_id: modelId,
        status: 'completed',
      });
      await loadRun();
    } catch (err: any) {
      throw err;
    }
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

  const handleContinueToDebate = async () => {
    if (!id) return;
    setIsContinuingToDebate(true);
    try {
      const debateRun = await api.continueToDebate(id);
      navigate(`/discussions/${debateRun.id}`);
    } catch (err: any) {
      alert(err.message || 'Gagal melanjutkan ke AI Debate');
      setIsContinuingToDebate(false);
    }
  };

  const handleStopDiscussion = async () => {
    if (!id) return;
    if (confirm('Apakah Anda yakin ingin menghentikan sementara sesi diskusi ini?')) {
      try {
        await api.stopDiscussion(id);
        await loadRun();
      } catch (err: any) {
        alert(err.message || 'Gagal menghentikan diskusi');
      }
    }
  };

  const handleResumeDiscussion = async () => {
    if (!id) return;
    try {
      await api.resumeDiscussion(id);
      await loadRun();
    } catch (err: any) {
      alert(err.message || 'Gagal melanjutkan diskusi');
    }
  };

  const handleSynthesisSubmit = async (data: {
    raw_synthesis: string;
    moderator_provider?: string;
  }) => {
    if (!id) return;
    try {
      await api.submitSynthesis(id, {
        ...data,
        allow_partial: isPartialSynthesis || run?.status === 'stopped',
      });
      await loadRun();
    } catch (err: any) {
      throw err;
    }
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

  // Debater models only (exclude moderator placeholder from debater responses)
  const debaterResponses = (run.responses || []).filter((r) => r.provider !== 'moderator');

  const currentStageResponses = debaterResponses.filter((r) => {
    if (run.mode === 'parallel') return true;
    if (selectedStageTab !== 'all') return r.stage === selectedStageTab;
    if (run.current_stage === 'completed' || run.current_stage === 'final_synthesis') return true;
    return r.stage === run.current_stage;
  });

  const availableStages = Array.from(new Set(debaterResponses.map((r) => r.stage)));

  const completedCount = currentStageResponses.filter((r) => r.status === 'completed').length;
  const hasMinimumResponses = debaterResponses.filter((r) =>
    (run.mode === 'parallel' ? true : r.stage === run.current_stage) && r.status === 'completed'
  ).length > 0;

  const canAdvanceStage =
    run.mode === 'debate' &&
    run.current_stage !== 'completed' &&
    run.current_stage !== 'final_synthesis' &&
    run.status === 'awaiting_input';

  const anyResponseCompletedInRun = debaterResponses.some((r) => r.status === 'completed');

  // Get active synthesis prompt for modal
  const synthesisPlaceholderResp = run.responses.find((r) => r.stage === 'final_synthesis');
  const synthPrompt = synthesisPlaceholderResp?.prompt_used || 'Prompt sintesis moderator AI Council...';

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
              {run.status === 'stopped' && (
                <span className="px-2 py-0.5 rounded text-[11px] font-bold uppercase bg-rose-500/20 text-rose-300 border border-rose-500/30">
                  Dihentikan (Stopped)
                </span>
              )}
            </div>
            <h1 className="text-lg font-bold text-white mt-0.5 line-clamp-1">
              {run.query}
            </h1>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2.5">
          <a
            href={api.getExportUrl(run.id)}
            download
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 text-xs font-semibold transition"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Ekspor Laporan</span>
          </a>

          {/* Parallel mode: Elevate to full debate */}
          {run.mode === 'parallel' && (
            <button
              onClick={handleContinueToDebate}
              disabled={isContinuingToDebate}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-bold text-xs transition shadow-lg shadow-amber-500/20 disabled:opacity-50"
              title="Lanjutkan analisis awal ini ke sesi AI Debate untuk kritik silang antarmodel"
            >
              <Flame className="w-3.5 h-3.5 fill-current" />
              <span>{isContinuingToDebate ? 'Menyiapkan Debat...' : 'Lanjutkan ke AI Debate'}</span>
            </button>
          )}

          {run.status !== 'completed' && run.status !== 'stopped' && (
            <button
              onClick={handleStopDiscussion}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 hover:bg-rose-950/40 text-rose-400 border border-rose-500/30 text-xs font-semibold transition"
            >
              <StopCircle className="w-3.5 h-3.5" />
              <span>Hentikan</span>
            </button>
          )}

          {run.status === 'stopped' && run.current_stage !== 'completed' && (
            <button
              onClick={handleResumeDiscussion}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition shadow-lg shadow-emerald-600/20"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Lanjutkan Diskusi</span>
            </button>
          )}

          {canAdvanceStage && (
            <button
              onClick={handleAdvanceStage}
              disabled={isAdvancing || !hasMinimumResponses}
              title={!hasMinimumResponses ? 'Harap isi minimal 1 respons sebelum lanjut' : undefined}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 disabled:opacity-40 disabled:cursor-not-allowed text-slate-950 font-bold text-xs transition shadow-lg shadow-emerald-500/20"
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
              onClick={() => {
                setIsPartialSynthesis(false);
                setIsSynthesisModalOpen(true);
              }}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition shadow-lg shadow-indigo-600/20"
            >
              <Award className="w-4 h-4" />
              <span>Isi Sintesis Konsensus</span>
            </button>
          )}

          {/* Partial Synthesis option if stopped or early conclusion desired */}
          {(run.status === 'stopped' || (run.mode === 'debate' && run.current_stage !== 'final_synthesis')) &&
            run.status !== 'completed' &&
            anyResponseCompletedInRun && (
              <button
                onClick={() => {
                  setIsPartialSynthesis(true);
                  setIsSynthesisModalOpen(true);
                }}
                className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-slate-900 hover:bg-indigo-950/40 text-indigo-300 border border-indigo-500/30 text-xs font-semibold transition"
                title="Tutup diskusi sekarang dan simpan sintesis atas respons yang tersedia"
              >
                <Award className="w-3.5 h-3.5" />
                <span>Sintesis Parsial</span>
              </button>
            )}
        </div>
      </div>

      {/* Parallel Mode Info Banner */}
      {run.mode === 'parallel' && (
        <div className="p-4 rounded-2xl bg-emerald-950/30 border border-emerald-500/30 text-xs text-slate-300 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <Sparkles className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>
              <strong>Mode Parallel Chat:</strong> Membandingkan jawaban mandiri setiap model dewan. Gunakan tombol <strong>Lanjutkan ke AI Debate</strong> untuk membawa hasil ini ke kritik silang dan sintesis akhir.
            </span>
          </div>
          <button
            onClick={handleContinueToDebate}
            disabled={isContinuingToDebate}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold text-xs transition shrink-0 shadow-md shadow-amber-500/20"
          >
            <Flame className="w-3.5 h-3.5 fill-current" />
            <span>{isContinuingToDebate ? 'Memproses...' : 'Lanjutkan ke AI Debate →'}</span>
          </button>
        </div>
      )}

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

      {/* Model Responses Section */}
      <div>
        {!hasMinimumResponses && run.mode === 'debate' && run.current_stage !== 'final_synthesis' && run.status === 'awaiting_input' && (
          <div className="p-3 mb-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center gap-2.5 text-xs text-amber-300">
            <AlertCircle className="w-4 h-4 shrink-0 text-amber-400" />
            <span>Harap salin dan isi minimal 1 respons AI di bawah ini sebelum melanjutkan ke tahap debat berikutnya.</span>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider">
              {run.mode === 'parallel'
                ? 'Respons Dewan AI (Parallel Analysis)'
                : `Respons Dewan AI (${(selectedStageTab === 'all' ? run.current_stage : selectedStageTab).replace('_', ' ')})`}
            </h3>

            {/* Stage filter pills for debate mode if multiple stages exist */}
            {run.mode === 'debate' && availableStages.length > 1 && (
              <div className="flex items-center gap-1.5 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs">
                <button
                  type="button"
                  onClick={() => setSelectedStageTab('all')}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition ${
                    selectedStageTab === 'all'
                      ? 'bg-emerald-600 text-white'
                      : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Semua ({debaterResponses.length})
                </button>
                {availableStages.map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => setSelectedStageTab(st)}
                    className={`px-2.5 py-1 rounded-lg text-xs font-medium transition capitalize ${
                      selectedStageTab === st
                        ? 'bg-emerald-600 text-white'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {st.replace('_', ' ')}
                  </button>
                ))}
              </div>
            )}
          </div>

          <span className="text-xs text-slate-400">
            {completedCount} dari {currentStageResponses.length} respons selesai
          </span>
        </div>

        {currentStageResponses.length === 0 ? (
          <div className="p-8 rounded-2xl bg-slate-900/60 border border-slate-800 text-center text-slate-400">
            <AlertCircle className="w-8 h-8 mx-auto text-amber-400 mb-2" />
            <h4 className="text-sm font-semibold text-slate-200">Belum Ada Kartu Respons</h4>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
              Belum ada respons dewan yang tercatat untuk tampilan ini. Silakan periksa kembali konfigurasi dewan Anda.
            </p>
          </div>
        ) : (
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
        )}
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
