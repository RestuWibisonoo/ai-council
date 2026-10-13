import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  PlusCircle,
  Columns,
  Flame,
  FolderKanban,
  FileText,
  History,
  KeyRound,
  Coins,
  Settings,
  Sparkles,
  ExternalLink
} from 'lucide-react';

interface SidebarProps {
  providersStatus?: { id: string; display_name: string; mode: string }[];
}

export const Sidebar: React.FC<SidebarProps> = ({ providersStatus = [] }) => {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/new-discussion', label: 'Diskusi Baru', icon: PlusCircle, highlight: true },
    { to: '/compare', label: 'Komparasi Model', icon: Columns },
    { to: '/debate', label: 'AI Debate', icon: Flame },
    { to: '/research', label: 'Ruang Riset', icon: FolderKanban },
    { to: '/documents', label: 'Dokumen & Sumber', icon: FileText },
    { to: '/history', label: 'Riwayat Percakapan', icon: History },
    { to: '/providers', label: 'Pengaturan Provider', icon: KeyRound },
    { to: '/usage', label: 'Penggunaan & Biaya', icon: Coins },
    { to: '/settings', label: 'Pengaturan Aplikasi', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-950/80 border-r border-slate-800 flex flex-col h-screen sticky top-0 backdrop-blur-xl z-20">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-emerald-500 to-indigo-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="font-bold text-base text-slate-100 tracking-tight leading-tight">
              AI Council
            </h1>
            <p className="text-[11px] text-emerald-400 font-medium tracking-wide">
              Workspace Riset & Debat
            </p>
          </div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 shadow-sm'
                    : item.highlight
                    ? 'text-emerald-300 hover:bg-emerald-950/40 hover:text-emerald-200'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                }`
              }
            >
              <Icon className="w-4 h-4 shrink-0" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Provider Quick Status Panel */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-900/30">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
            Dewan Terhubung
          </span>
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
        </div>
        <div className="grid grid-cols-2 gap-1.5 text-[11px]">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-slate-800/60 text-slate-300">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            <span className="truncate">ChatGPT</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-slate-800/60 text-slate-300">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            <span className="truncate">Claude</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-slate-800/60 text-slate-300">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
            <span className="truncate">Gemini</span>
          </div>
          <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-slate-800/60 text-slate-300">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
            <span className="truncate">NotebookLM</span>
          </div>
        </div>
        <div className="mt-3 pt-2.5 border-t border-slate-800/50 flex items-center justify-between text-[11px] text-slate-400">
          <span>Mode Utama:</span>
          <span className="text-emerald-400 font-medium">Manual Bridge</span>
        </div>
      </div>
    </aside>
  );
};
