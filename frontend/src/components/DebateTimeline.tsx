import React from 'react';
import { CheckCircle2, Clock, PlayCircle, Award } from 'lucide-react';

interface DebateTimelineProps {
  currentStage: string;
  currentRound: number;
  maxRounds: number;
}

export const DebateTimeline: React.FC<DebateTimelineProps> = ({
  currentStage,
  currentRound,
  maxRounds,
}) => {
  const stages = [
    { id: 'initial_analysis', label: '1. Analisis Awal', desc: 'Argumen & hipotesis awal' },
    { id: 'cross_critique', label: '2. Kritik Silang', desc: 'Uji celah logika & klaim' },
    { id: 'rebuttal', label: '3. Sanggahan', desc: 'Pertahanan & koreksi argumen' },
    { id: 'final_synthesis', label: '4. Sintesis Moderator', desc: 'Konsensus 8 poin' },
  ];

  const getStageIndex = (stage: string) => {
    switch (stage) {
      case 'initial_analysis':
        return 0;
      case 'cross_critique':
        return 1;
      case 'rebuttal':
        return 2;
      case 'final_synthesis':
        return 3;
      case 'completed':
        return 4;
      default:
        return 0;
    }
  };

  const currentIndex = getStageIndex(currentStage);

  return (
    <div className="w-full bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-sm backdrop-blur-md">
      <div className="flex items-center justify-between mb-3 px-1">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
            Alur Debat Intelektual
          </span>
          <span className="px-2 py-0.5 rounded-full text-[11px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
            Putaran {currentRound} dari {maxRounds}
          </span>
        </div>
        <span className="text-xs text-slate-400">
          Tahap Aktif: <strong className="text-slate-200 capitalize">{currentStage.replace('_', ' ')}</strong>
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {stages.map((st, idx) => {
          const isDone = currentIndex > idx;
          const isCurrent = currentIndex === idx;

          return (
            <div
              key={st.id}
              className={`p-3 rounded-xl border transition-all ${
                isCurrent
                  ? 'bg-emerald-500/10 border-emerald-500/50 shadow-sm shadow-emerald-500/10'
                  : isDone
                  ? 'bg-slate-950/40 border-slate-800 text-slate-300'
                  : 'bg-slate-950/20 border-slate-800/40 text-slate-500'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className={`text-xs font-bold ${isCurrent ? 'text-emerald-400' : isDone ? 'text-slate-200' : 'text-slate-500'}`}>
                  {st.label}
                </span>
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : isCurrent ? (
                  <PlayCircle className="w-4 h-4 text-emerald-400 animate-pulse" />
                ) : (
                  <Clock className="w-4 h-4 text-slate-600" />
                )}
              </div>
              <p className="text-[11px] text-slate-400 line-clamp-1">
                {st.desc}
              </p>
            </div>
          );
        })}
      </div>
    </div>
  );
};
