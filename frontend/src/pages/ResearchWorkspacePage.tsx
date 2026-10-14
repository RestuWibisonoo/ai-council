import React, { useState, useEffect } from 'react';
import {
  FolderKanban,
  Plus,
  BookOpen,
  FileText,
  ExternalLink,
  Copy,
  Check,
  Send,
  Trash2,
  Bookmark,
  Sparkles,
  AlertCircle
} from 'lucide-react';
import {
  api,
  ResearchProject,
  DocumentItem,
  ConversationItem
} from '../services/api';

export const ResearchWorkspacePage: React.FC = () => {
  const [projects, setProjects] = useState<ResearchProject[]>([]);
  const [selectedProject, setSelectedProject] = useState<ResearchProject | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [conversations, setConversations] = useState<ConversationItem[]>([]);

  // Project Creation Modal / Form State
  const [isCreating, setIsCreating] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newQuestion, setNewQuestion] = useState('');

  const [savedNotes, setSavedNotes] = useState('');
  const [isSavingNotes, setIsSavingNotes] = useState(false);

  const loadProjects = async () => {
    try {
      const projs = await api.getProjects();
      setProjects(projs);
      if (projs.length > 0 && !selectedProject) {
        setSelectedProject(projs[0]);
      }
    } catch (err) {
      console.error('Failed to load projects:', err);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      setSavedNotes(selectedProject.notes || '');
      // Load linked docs & conversations
      Promise.all([
        api.getDocuments(selectedProject.id),
        api.getConversations(selectedProject.id),
      ]).then(([docs, convs]) => {
        setDocuments(docs);
        setConversations(convs);
      });
    }
  }, [selectedProject]);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    try {
      const created = await api.createProject({
        title: newTitle.trim(),
        description: newDesc.trim() || undefined,
        research_question: newQuestion.trim() || undefined,
      });
      setProjects([created, ...projects]);
      setSelectedProject(created);
      setIsCreating(false);
      setNewTitle('');
      setNewDesc('');
      setNewQuestion('');
    } catch (err: any) {
      alert(err.message || 'Gagal membuat proyek');
    }
  };

  const handleDeleteProject = async (projectId: string) => {
    if (confirm('Hapus proyek penelitian ini beserta referensinya?')) {
      await api.deleteProject(projectId);
      const remaining = projects.filter((p) => p.id !== projectId);
      setProjects(remaining);
      setSelectedProject(remaining.length > 0 ? remaining[0] : null);
    }
  };

  const handleSaveNotes = async () => {
    if (!selectedProject) return;
    setIsSavingNotes(true);
    try {
      await fetch(`/api/research/projects/${selectedProject.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: savedNotes }),
      });
      alert('Catatan penelitian berhasil disimpan!');
    } catch {
      alert('Gagal menyimpan catatan');
    } finally {
      setIsSavingNotes(false);
    }
  };

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-7">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 text-xs font-semibold mb-2">
            <FolderKanban className="w-3.5 h-3.5" />
            <span>Workspace Manajemen Riset</span>
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            Ruang Penelitian Terpadu
          </h1>
          <p className="text-sm text-slate-400 mt-0.5">
            Kelola proyek penelitian, pertanyaan sentral, catatan sintesis, dan sumber dokumen dalam satu tempat.
          </p>
        </div>

        <button
          onClick={() => setIsCreating(true)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-xs transition shadow-lg shadow-emerald-500/20"
        >
          <Plus className="w-4 h-4" />
          <span>Buat Proyek Baru</span>
        </button>
      </div>

      {/* Main Layout: Left Projects Selector & Right Project Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Project Selector Sidebar */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider px-1">
            Daftar Proyek Riset
          </h3>

          {projects.length === 0 ? (
            <div className="p-6 rounded-2xl bg-slate-900/40 border border-slate-800 text-center text-xs text-slate-500">
              Belum ada proyek riset.
            </div>
          ) : (
            <div className="space-y-1.5">
              {projects.map((p) => {
                const isSelected = selectedProject?.id === p.id;
                return (
                  <div
                    key={p.id}
                    onClick={() => setSelectedProject(p)}
                    className={`p-3.5 rounded-xl border cursor-pointer transition text-left ${
                      isSelected
                        ? 'bg-indigo-950/40 border-indigo-500/80 text-white shadow-md'
                        : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                    }`}
                  >
                    <h4 className="font-bold text-sm truncate">{p.title}</h4>
                    <p className="text-[11px] text-slate-500 truncate mt-0.5">
                      {p.research_question || 'Belum ada pertanyaan riset'}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Selected Project Workspace Panel */}
        <div className="lg:col-span-3 space-y-6">
          {selectedProject ? (
            <>
              {/* Project Meta Card */}
              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3">
                  <div>
                    <h2 className="text-xl font-bold text-white">
                      {selectedProject.title}
                    </h2>
                    <p className="text-xs text-slate-400 mt-1">
                      {selectedProject.description || 'Tidak ada deskripsi'}
                    </p>
                  </div>
                  <button
                    onClick={() => handleDeleteProject(selectedProject.id)}
                    className="p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition"
                    title="Hapus proyek ini"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                <div className="mt-4 p-4 rounded-xl bg-slate-950/60 border border-slate-800">
                  <span className="text-[11px] font-bold text-indigo-400 uppercase tracking-wider block mb-1">
                    Pertanyaan Penelitian Sentral:
                  </span>
                  <p className="text-sm font-semibold text-slate-200">
                    "{selectedProject.research_question || 'Silakan tentukan pertanyaan penelitian'}"
                  </p>
                </div>
              </div>

              {/* Research Notes & Synthesis Workspace */}
              <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Bookmark className="w-4 h-4 text-emerald-400" />
                    <h3 className="font-bold text-sm text-slate-200 uppercase tracking-wider">
                      Catatan & Sintesis Penelitian Proyek
                    </h3>
                  </div>
                  <button
                    onClick={handleSaveNotes}
                    disabled={isSavingNotes}
                    className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition"
                  >
                    {isSavingNotes ? 'Menyimpan...' : 'Simpan Catatan'}
                  </button>
                </div>
                <textarea
                  value={savedNotes}
                  onChange={(e) => setSavedNotes(e.target.value)}
                  placeholder="Ketik catatan penelitian bebas, hipotesis awal, atau gabungan temuan multi-model di sini..."
                  rows={8}
                  className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 placeholder-slate-500 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500 transition font-sans leading-relaxed"
                />
              </div>
            </>
          ) : (
            <div className="p-12 text-center text-slate-500 bg-slate-900/40 rounded-2xl border border-slate-800">
              Pilih atau buat proyek riset untuk memulai.
            </div>
          )}
        </div>
      </div>

      {/* Create Project Modal */}
      {isCreating && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Buat Proyek Riset Baru</h3>
            <form onSubmit={handleCreateProject} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Nama Proyek</label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="Contoh: Riset Ketahanan Algoritma LLM"
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Pertanyaan Penelitian Sentral</label>
                <textarea
                  value={newQuestion}
                  onChange={(e) => setNewQuestion(e.target.value)}
                  placeholder="Contoh: Bagaimana metode terbaik memvalidasi output model pada regulasi perbankan?"
                  rows={3}
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Deskripsi Singkat</label>
                <input
                  type="text"
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  placeholder="Tujuan dan ruang lingkup riset..."
                  className="w-full px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-slate-200 text-sm focus:outline-none focus:ring-1 focus:ring-emerald-500"
                />
              </div>
              <div className="pt-2 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsCreating(false)}
                  className="px-4 py-2 rounded-xl text-slate-400 hover:text-slate-200 text-xs font-semibold"
                >
                  Batal
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold shadow-md shadow-emerald-500/20"
                >
                  Simpan Proyek
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
