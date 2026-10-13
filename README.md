# AI Council — Multi-AI Discussion & Research Workspace

AI Council adalah platform kolaboratif dan ruang penelitian pribadi yang memungkinkan Anda mengelola diskusi bersama **ChatGPT**, **Claude**, **Gemini**, dan sumber riset **NotebookLM** dalam satu antarmuka terpadu.

Aplikasi ini dirancang khusus untuk berjalan secara lokal di Mac (Apple Silicon & Intel) maupun di-deploy ke server pribadi menggunakan Docker Compose.

---

## 1. Arsitektur & Prinsip Utama

1. **Mode A — Manual Bridge (Default & 100% Gratis)**:
   - Tidak memerlukan kredit API berbayar.
   - Anda dapat memanfaatkan akun antarmuka gratis Anda (**ChatGPT Go/Free**, **Claude Free**, **Gemini Pro Web**, dan **NotebookLM**).
   - Aplikasi otomatis memformat prompt, menyediakan tombol 1-klik untuk membuka layanan resmi, menyalin prompt, dan kolom penempelan respons kembali ke dewan.
2. **Mode B — Official API (Opsional)**:
   - Tersedia adapter resmi untuk OpenAI API, Anthropic API, dan Google Gemini API jika Anda memiliki API key pribadi.
   - Kunci API disimpan aman di backend lokal, tidak pernah dikirim ke frontend, dan tidak pernah disimpan dalam git.
3. **State Machine Debat Multi-Putaran**:
   - 4 Tahap Terstruktur: **Initial Analysis** &rarr; **Cross-Critique** &rarr; **Rebuttal** &rarr; **Final Synthesis**.
   - Moderator menghasilkan konsensus berbasis 8 poin fakta (bukan suara mayoritas fiktif).
4. **Knowledge Engine Lokal**:
   - Ekstraksi PDF menggunakan PyMuPDF (`fitz`), pengindeksan potongan halaman lokal, dan pencarian kutipan berbasis skor relevansi.
   - Membedakan kutipan asli terverifikasi dari ringkasan spekulatif.

---


## Auto Copy-Paste Bridge (Playwright lokal)

Bridge opsional ini membuka browser Chromium yang terlihat dan mengisi prompt ke antarmuka resmi ChatGPT, Gemini, Claude, atau NotebookLM. Bridge **tidak mengirim prompt otomatis**: periksa isi prompt lalu klik tombol kirim sendiri. Login dilakukan manual di situs resmi; aplikasi tidak mengambil cookie, token, atau melewati autentikasi.

### Setup lokal

1. Jalankan backend dari mesin desktop yang memiliki sesi grafis aktif (bukan container/headless server):
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m playwright install chromium
   python run.py
   ```
2. Jalankan frontend seperti biasa dari `frontend` dengan `npm install` dan `npm run dev`.
3. Buka Manual Bridge pada respons diskusi, lalu pilih **Isi via Playwright**.
4. Saat pertama kali, login sendiri di jendela Chromium yang terbuka. Klik tombol tersebut lagi setelah login jika prompt belum terisi.
5. Periksa prompt dan kirim sendiri di halaman provider. Salin jawaban ke kolom respons AI Council untuk melanjutkan alur diskusi.

Profil browser tersimpan lokal di `data/playwright-profile` (direktori `data/` diabaikan Git). Perlakukan profil ini sebagai data privat. Jangan jalankan bridge pada server publik; endpoint dirancang untuk penggunaan lokal tepercaya. Jika UI provider berubah dan kolom pesan tidak ditemukan, gunakan tombol salin/manual yang sudah ada.

## 2. Struktur Repositori

```text
ai-council/
├── backend/
│   ├── app/
│   │   ├── adapters/          # OpenAI, Anthropic, Gemini, dan Base Adapters
│   │   ├── models/            # SQLAlchemy database models (12 entitas)
│   │   ├── routers/           # API routes (health, discussions, documents, providers, research, usage)
│   │   ├── schemas/           # Pydantic v2 schemas
│   │   ├── services/          # Orchestrator, PromptBuilder, DocumentService, ProviderManager
│   │   ├── config.py          # Konfigurasi aplikasi & settings
│   │   ├── database.py        # SQLAlchemy session & SQLite engine
│   │   └── main.py            # Entrypoint FastAPI
│   ├── alembic/               # Skrip migrasi database
│   ├── tests/                 # Automated unit & integration test suites
│   ├── requirements.txt       # Kunci dependensi Python
│   └── run.py                 # Runner backend lokal
├── frontend/
│   ├── src/
│   │   ├── components/        # Sidebar, ManualBridgeModal, DebateTimeline, ResponseCard, SynthesisView, dll.
│   │   ├── pages/             # Dashboard, NewDiscussion, DiscussionDetail, Compare, Debate, Research, Documents, History, Providers, Usage, Settings
│   │   ├── services/api.ts    # TypeScript API Client
│   │   ├── App.tsx            # React router & layout
│   │   └── index.css          # Tailwind CSS & glassmorphic tokens
│   ├── package.json
│   └── vite.config.ts         # Vite server proxy ke backend 127.0.0.1:8000
├── data/                      # Direktori persisten lokal (diabaikan git)
│   ├── uploads/               # File PDF & dokumen yang diunggah
│   ├── ai_council.db          # Database SQLite lokal
│   └── provider_secrets.json  # Kunci rahasia API tersimpan dengan chmod 0600
├── docker-compose.yml         # Konfigurasi deployment Docker
├── Dockerfile.backend
├── Dockerfile.frontend
├── .env.example
├── .gitignore
└── README.md
```

---

## 3. Prasyarat Lingkungan (Mac)

- **macOS** 12 (Monterey) atau yang lebih baru.
- **Python** 3.9+ (disarankan menggunakan virtual environment `.venv`).
- **Node.js** v18+ atau v20+ dan **npm** v9+.

---

## 4. Cara Instalasi & Menjalankan di Mac

### Langkah 1: Kloning & Masuk ke Folder Proyek
```bash
git clone https://github.com/RestuWibisonoo/ai-council.git
cd ai-council
```

### Langkah 2: Setup Backend Python
```bash
# 1. Buat dan aktifkan virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependensi
pip install -r backend/requirements.txt

# 3. Jalankan migrasi database SQLite lokal
export PYTHONPATH=backend
cd backend && alembic upgrade head && cd ..

# 4. Jalankan server FastAPI backend
source .venv/bin/activate
export PYTHONPATH=backend
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Backend akan aktif di: `http://127.0.0.1:8000` (Dokumentasi API Swagger di `http://127.0.0.1:8000/docs`).

### Langkah 3: Setup Frontend React (Buka Terminal Baru)
```bash
cd frontend

# 1. Install paket frontend
npm install

# 2. Jalankan server pengembangan Vite
npm run dev
```
Frontend web siap diakses di peramban (browser) Anda: **`http://127.0.0.1:5173`**.

---

## 5. Menjalankan via Docker Compose (Opsi Server Pribadi)

Jika ingin menjalankan aplikasi secara terisolasi atau di server Linux:
```bash
docker compose up --build -d
```
Aplikasi frontend akan tersedia di `http://127.0.0.1:5173` dan backend di `http://127.0.0.1:8000`. Port dibatasi hanya dapat diakses melalui localhost demi keamanan. Data persisten tersimpan aman di folder `./data`.

---

## 6. Alur Penggunaan (Workflow)

### A. Alur Diskusi Paralel (Mode 1)
1. Buka menu **Diskusi Baru** (`/new-discussion`).
2. Masukkan pertanyaan (misal: perbandingan teknologi atau evaluasi arsitektur).
3. Pilih **Parallel Chat**, tentukan model AI dewan yang ingin diajak berdiskusi.
4. Klik **Mulai Diskusi AI Council**.
5. Pada setiap kartu model:
   - Klik **Buka Manual Bridge & Salin Prompt**.
   - Klik tombol **Buka Layanan AI Resmi** untuk membuka tab ChatGPT/Claude/Gemini.
   - Tempel prompt, salin hasil jawabannya dari AI tersebut, dan tempelkan kembali ke kolom input aplikasi.
   - Klik **Simpan Respons ke Dewan**.
6. Jawaban tersimpan rapi dan dapat dibandingkan secara langsung.

### B. Alur AI Debate & Konsensus Moderator (Mode 2)
1. Pilih mode **AI Debate** dan tentukan jumlah putaran (1 sampai 3 putaran).
2. **Tahap 1 (Initial Analysis)**: Masing-masing model memberikan hipotesis dan bukti awal.
3. Klik **Lanjut ke Tahap Berikutnya** &rarr; **Tahap 2 (Cross-Critique)**: Sistem menyusun prompt kritik silang untuk memeriksa:
   - Klaim yang tidak memiliki bukti.
   - Kontradiksi internal dan antarmodel.
   - Asumsi tersembunyi yang belum teruji.
   - Kesalahan logika / fallacy.
4. Klik **Lanjut ke Tahap Berikutnya** &rarr; **Tahap 3 (Rebuttal)**: Model menanggapi kritik, mengakui kekeliruan, atau mempertahankan argumen dengan bukti baru.
5. Klik **Lanjut ke Tahap Berikutnya** &rarr; **Tahap 4 (Final Synthesis)**:
   - Sistem merangkum seluruh transkrip perdebatan ke dalam prompt moderator.
   - Moderator menghasilkan sintesis 8 bagian: *Ringkasan Masalah*, *Kesepakatan Antarmodel*, *Perbedaan Pendapat*, *Kritik Belum Terselesaikan*, *Bukti Pendukung*, *Rekomendasi*, *Ketidakpastian*, dan *Referensi Sumber*.
6. Klik **Ekspor Laporan** untuk mengunduh dokumen laporan Markdown lengkap.

### C. Alur Knowledge Engine & NotebookLM (Mode 3)
1. Masuk ke menu **Dokumen & Sumber** (`/documents`).
2. Unggah file PDF, TXT, atau Markdown. PyMuPDF otomatis memecah teks per halaman dan membuat indeks pencarian.
3. Masuk ke **Ruang Riset** (`/research`), buat proyek penelitian baru.
4. Gunakan generator prompt NotebookLM, buka tautan resmi NotebookLM, dan simpan catatan temuan penelitian Anda.

---

## 7. Konfigurasi Provider: Membedakan Layanan Web & Model API

Penting dipahami bahwa **langganan antarmuka web tidak otomatis memberikan akses API**. AI Council membedakan keduanya secara tegas:

| Provider | Akun / Antarmuka Web (Mode A: Manual) | Model API Resmi (Mode B: Optional API) | Status Integrasi |
| :--- | :--- | :--- | :--- |
| **ChatGPT** | ChatGPT Go, ChatGPT Free, ChatGPT Plus (`https://chatgpt.com`) | `gpt-4o`, `gpt-4o-mini`, `o3-mini` | Manual Bridge aktif; API opsional jika memiliki API key |
| **Claude** | Claude Free, Claude Pro (`https://claude.ai`) | `claude-3-7-sonnet-20250219`, `claude-3-5-sonnet-20241022`, `claude-3-5-haiku-20241022` | Manual Bridge aktif; API opsional jika memiliki API key |
| **Gemini** | Gemini Pro Web, Gemini Free, Advanced (`https://gemini.google.com`) | `gemini-2.5-flash`, `gemini-2.5-pro`, `gemini-1.5-flash` | Manual Bridge aktif; API opsional jika memiliki API key |
| **NotebookLM** | Akun pengguna pribadi (`https://notebooklm.google.com`) | *Tidak tersedia API publik untuk akun standar* | Eksklusif via Manual Bridge (100% Gratis) |

> **Catatan Transparansi Biaya:**
> - Pada **Mode A (Manual Bridge)**, token yang ditampilkan adalah estimasi volume teks untuk referensi pengguna. Biaya API adalah **Rp 0** dan tidak ada biaya tagihan ke pengguna.
> - Pada **Mode B (Official API)**, token dilaporkan sesuai metadata resmi provider dan estimasi biaya dihitung berdasarkan tarif per 1M token resmi.

---

## 8. Backup & Restore Data Lokal

Semua data persisten berada di folder `./data`:
```bash
# Melakukan backup arsip data:
tar -czvf ai_council_backup_$(date +%F).tar.gz data/

# Melakukan restore arsip data:
tar -xzvf ai_council_backup_2026-10-13.tar.gz
```

---

## 9. Menjalankan Automated Tests

Test suite komprehensif menguji pembuatan percakapan, alur manual bridge, transisi state machine debat, ekstraksi PyMuPDF, dan integrasi full-flow:
```bash
source .venv/bin/activate
export PYTHONPATH=backend
pytest -v backend/tests
```
Semua 7 suite pengujian unit dan integrasi akan dieksekusi menggunakan in-memory database terisolasi tanpa memerlukan kredensial berbayar.

---

## 10. Dokumentasi Endpoint Backend

| Metode | Endpoint | Keterangan |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Status kesehatan sistem dan database |
| `POST` | `/api/discussions` | Memulai sesi diskusi/debat baru |
| `GET` | `/api/discussions/{run_id}` | Mengambil detail dan respons sesi diskusi |
| `POST` | `/api/discussions/{run_id}/responses` | Mengirim respons manual (Manual Bridge) |
| `POST` | `/api/discussions/{run_id}/advance` | Memajukan tahapan debat (Critique &rarr; Rebuttal &rarr; Synthesis) |
| `POST` | `/api/discussions/{run_id}/synthesis` | Menyimpan sintesis moderator 8 poin |
| `POST` | `/api/discussions/{run_id}/stop` | Menghentikan sesi diskusi |
| `GET` | `/api/discussions/{run_id}/export` | Mengunduh laporan hasil dalam format Markdown |
| `GET` | `/api/conversations` | Daftar seluruh riwayat percakapan |
| `DELETE` | `/api/conversations/{id}` | Menghapus percakapan |
| `POST` | `/api/documents/upload` | Mengunggah PDF/TXT dan mengekstrak teks via PyMuPDF |
| `GET` | `/api/documents` | Daftar dokumen penelitian |
| `POST` | `/api/documents/search` | Pencarian teks dan potongan dokumen relevan |
| `DELETE` | `/api/documents/{id}` | Menghapus dokumen dari disk dan indeks |
| `GET` | `/api/providers` | Konfigurasi provider dan status API key |
| `PUT` | `/api/providers/{id}` | Memperbarui mode (manual/api), model, dan batas biaya |
| `POST` | `/api/providers/{id}/test` | Menguji konektivitas provider |
| `GET` | `/api/research/projects` | Daftar proyek penelitian terstruktur |
| `GET` | `/api/research/notebooklm-prompt` | Generator prompt riset untuk NotebookLM |
| `GET` | `/api/usage/summary` | Audit pemisahan penggunaan manual (Rp 0) vs API |
