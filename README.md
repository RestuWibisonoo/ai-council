# AI Council — Free Multi-Provider AI Debate Platform & Research Workspace

AI Council adalah platform kolaboratif dan ruang penelitian terbuka yang memungkinkan Anda menjalankan **Debat Multi-AI Otomatis dalam 1-Klik** menggunakan model-model AI gratis atau berkuota gratis dari berbagai keluarga (**DeepSeek, Qwen / Alibaba, Meta Llama, GLM, Ollama Lokal, Google Gemini, Anthropic Claude, dan OpenAI ChatGPT**) dalam satu antarmuka terpadu.

Aplikasi ini dirancang khusus dengan **Zero-Cost Mode** aktif secara default, memastikan Anda tidak pernah mengeluarkan biaya tagihan API yang tidak disengaja.

---

## 1. Arsitektur & Prinsip Utama

1. **Mode Bebas Biaya (Zero-Cost Mode — Prioritas Mutlak)**:
   - Memvalidasi metadata harga resmi setiap model (`pricing.prompt == 0.0` dan `pricing.completion == 0.0`).
   - Secara default **menolak** model berbayar atau model yang harga gratisnya tidak dapat diverifikasi.
   - Tidak pernah melakukan fallback otomatis ke model berbayar.
2. **Debat Otomatis 1-Klik (Single-Prompt Autonomous Debate)**:
   - Cukup masukkan topik atau pertanyaan, pilih peserta AI dari berbagai keluarga, dan klik **Mulai Diskusi**.
   - Sistem menjalankan seluruh siklus 4 tahapan secara otomatis:
     - **Stage 1 — Initial Analysis**: Analisis independen dari setiap model.
     - **Stage 2 — Cross-Critique**: Kritik silang otomatis membaca jawaban peserta lain untuk mendeteksi kelemahan logika dan asumsi.
     - **Stage 3 — Rebuttal / Refinement**: Pembelaan atau perbaikan argumen atas kritik yang diterima.
     - **Stage 4 — Final Synthesis**: Moderator menyusun laporan konsensus 8 bagian berdasarkan seluruh jawaban yang valid.
3. **Multi-Provider & Dynamic Model Catalog**:
   - **OpenRouter Free Models**: Akses dinamis ke model open-weight gratis (DeepSeek R1/V3, Qwen 2.5, Meta Llama 3.3, Mistral, Nemotron).
   - **Alibaba Cloud Model Studio (DashScope)**: Adapter resmi Qwen langsung (`DASHSCOPE_API_KEY`).
   - **DeepSeek API Direct**: Adapter resmi DeepSeek (`DEEPSEEK_API_KEY`) dengan proteksi Zero-Cost Mode.
   - **Ollama Local**: Eksekusi model lokal tanpa internet (`http://localhost:11434`), 100% privat dan gratis.
   - **Official API Connectors**: Konektor API langsung untuk OpenAI (ChatGPT), Anthropic (Claude), dan Google Gemini.
4. **Isolasi Kegagalan & Concurrency**:
   - Pemanggilan model dieksekusi secara asinkron dan paralel dengan batas concurrency yang aman.
   - Kegagalan salah satu model (misal: rate limit 429 atau kuota habis) tidak menggagalkan peserta lain yang masih berhasil.
5. **Ekspor Laporan Lengkap**:
   - Hasil debat dan sintesis moderator dapat diekspor langsung dalam format **Markdown (.md)** dan **Plain Text (.txt)**.

---

## 2. Struktur Repositori

```text
ai-council/
├── backend/
│   ├── app/
│   │   ├── adapters/          # OpenAI, Anthropic, Gemini, OpenRouter, Qwen, DeepSeek, Ollama
│   │   ├── models/            # SQLAlchemy database models (12 entitas)
│   │   ├── routers/           # API routes (health, discussions, documents, providers, research, usage)
│   │   ├── schemas/           # Pydantic v2 schemas
│   │   ├── services/          # Orchestrator (Auto Debate Engine), PromptBuilder, DocumentService, ProviderManager
│   │   ├── config.py          # Konfigurasi aplikasi & settings
│   │   ├── database.py        # SQLAlchemy session & SQLite engine
│   │   └── main.py            # Entrypoint FastAPI
│   ├── alembic/               # Skrip migrasi database
│   ├── tests/                 # Automated unit & integration test suites (45 tests)
│   ├── requirements.txt       # Kunci dependensi Python
│   └── run.py                 # Runner backend lokal
├── frontend/
│   ├── src/
│   │   ├── components/        # Sidebar, ResponseCard, DebateTimeline, SynthesisView, ManualBridgeModal, dll.
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

## 3. Prasyarat Lingkungan (Mac & Linux)

- **macOS** 12+ atau **Linux** (Ubuntu/Debian).
- **Python** 3.9+ (disarankan menggunakan virtual environment `.venv`).
- **Node.js** v18+ atau v20+ dan **npm** v9+.
- *(Opsional)* **Ollama** jika ingin menjalankan model open-source lokal di mesin sendiri.

---

## 4. Cara Instalasi & Menjalankan

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
Frontend web siap diakses di browser Anda: **`http://127.0.0.1:5173`**.

---

## 5. Konfigurasi Provider & Kunci API Gratis

Salin file konfigurasi lingkungan:
```bash
cp .env.example .env
```

### Variabel Environment Penting:
```env
# Multi-Provider Gratis (OpenRouter, DashScope, DeepSeek, Ollama)
OPENROUTER_API_KEY="sk-or-v1-xxxxxxxx"
DASHSCOPE_API_KEY=""
DEEPSEEK_API_KEY=""
OLLAMA_BASE_URL="http://localhost:11434"

# Keamanan Biaya: Zero-Cost Mode (Default: true)
AI_COUNCIL_ZERO_COST_MODE=true
MAX_DEBATE_ROUNDS=3
MAX_REQUESTS_PER_RUN=30
MAX_TOKENS_PER_RESPONSE=2048
```

### Panduan Mendapatkan Kunci API Gratis:

1. **OpenRouter (Satu Kunci untuk Beragam Model Gratis)**:
   - Kunjungi [openrouter.ai/keys](https://openrouter.ai/keys) dan buat akun gratis.
   - Buat kunci API baru (bebas biaya, tanpa perlu deposit saldo awal untuk model gratis).
   - Simpan kunci di `OPENROUTER_API_KEY` pada `.env`.
   - AI Council otomatis mengambil katalog model yang berakhiran `:free` dan berharga $0.00 (misalnya: `deepseek/deepseek-r1:free`, `qwen/qwen-2.5-72b-instruct:free`, `meta-llama/llama-3.3-70b-instruct:free`).

2. **Alibaba Cloud Model Studio / Qwen (DashScope)**:
   - Dapatkan kuota promosi gratis di [Alibaba Cloud Model Studio](https://www.alibabacloud.com/help/en/model-studio/new-free-quota).
   - Masukkan kunci di `DASHSCOPE_API_KEY`.

3. **Ollama (Model Lokal — 100% Offline & Gratis)**:
   - Pasang Ollama dari [ollama.com](https://ollama.com).
   - Jalankan model yang diinginkan di terminal, misalnya: `ollama run llama3.2` atau `ollama run qwen2.5:7b`.
   - AI Council otomatis mendeteksi model lokal yang terpasang melalui `http://localhost:11434`.

4. **DeepSeek Direct API**:
   - Jika memiliki saldo DeepSeek, isi `DEEPSEEK_API_KEY`.
   - Dalam **Zero-Cost Mode**, DeepSeek Direct akan diblokir secara default kecuali jika biaya telah diverifikasi atau Zero-Cost Mode dinonaktifkan oleh pengguna.

---

## 6. Alur Debat Otomatis 1-Klik (Single Prompt Debate)

1. Buka menu **Diskusi Baru** (`/new-discussion`).
2. Masukkan topik / permasalahan yang ingin diperdebatkan.
3. Pilih mode **AI Debate**.
4. Aktifkan sakelar **Debat Otomatis (1-Klik)**.
5. Pilih minimal 2 model peserta dari katalog model gratis (misalnya: *DeepSeek R1 Free*, *Qwen 2.5 Free*, dan *Llama 3.3 Free*).
6. Tentukan jumlah putaran (1 sampai 3 putaran).
7. Klik **Mulai Debat AI Council**.
8. Sistem akan mengeksekusi:
   - **Stage 1 (Initial Analysis)** secara paralel.
   - **Stage 2 (Cross-Critique)** otomatis saat Stage 1 selesai.
   - **Stage 3 (Rebuttal)** otomatis saat Stage 2 selesai.
   - **Stage 4 (Final Synthesis)** moderator menyusun konsensus menyeluruh.
9. Anda dapat menghentikan jalannya debat kapan saja dengan tombol **Hentikan Diskusi** atau mengunduh hasilnya dengan tombol **Ekspor Laporan** (.md dan .txt).

---

## 7. Arsitektur Otomasi Penuh (Zero-Cost & Direct API)

AI Council kini beroperasi 100% otomatis tanpa memerlukan mekanisme Manual Bridge. Debat antarmodel, kritik silang, sanggahan, dan sintesis moderator dieksekusi secara otonom melalui API gratis (OpenRouter Free Tier, Ollama Lokal) maupun API resmi terkonfigurasi.

---

## 8. Menjalankan Automated Tests

Seluruh alur Zero-Cost Mode, katalog OpenRouter dinamis, state machine debat otomatis, isolasi kegagalan, dan ekspor diuji secara menyeluruh dengan API mock terisolasi:

```bash
source .venv/bin/activate
export PYTHONPATH=backend
pytest -v backend/tests
```

**Hasil Pengujian:**
- Seluruh unit & integration test lulus tanpa error.

---

## 9. Dokumentasi Endpoint Backend

| Metode | Endpoint | Keterangan |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Status kesehatan sistem dan database |
| `POST` | `/api/discussions` | Membuat sesi diskusi/debat baru (mendukung `auto_run`) |
| `GET` | `/api/discussions/{run_id}` | Mengambil detail dan respons sesi diskusi |
| `POST` | `/api/discussions/{run_id}/run-auto` | Memicu eksekusi otomatis tahapan debat di background |
| `POST` | `/api/discussions/{run_id}/responses` | Memperbarui respons model (kompatibilitas riwayat lama) |
| `POST` | `/api/discussions/{run_id}/advance` | Memajukan tahapan debat (Critique &rarr; Rebuttal &rarr; Synthesis) |
| `POST` | `/api/discussions/{run_id}/synthesis` | Menyimpan sintesis moderator 8 poin |
| `POST` | `/api/discussions/{run_id}/stop` | Menghentikan sesi diskusi |
| `GET` | `/api/discussions/{run_id}/export` | Mengunduh laporan hasil dalam format Markdown & Plain Text |
| `GET` | `/api/providers/catalog/models` | Mengambil katalog dinamis model gratis & verifikasi harga $0.00 |
| `GET` | `/api/providers` | Konfigurasi provider dan status API key |
| `PUT` | `/api/providers/{id}` | Memperbarui model dan batas biaya provider API |
| `POST` | `/api/documents/upload` | Mengunggah PDF/TXT dan mengekstrak teks via PyMuPDF |
| `GET` | `/api/documents` | Daftar dokumen penelitian |
| `POST` | `/api/documents/search` | Pencarian teks dan potongan dokumen relevan |
| `GET` | `/api/usage/summary` | Audit pelacakan penggunaan token dan estimasi biaya API |

---

## 10. Lisensi

Dibuat untuk penelitian, edukasi, dan evaluasi model kecerdasan buatan multi-agen secara independen dan hemat biaya.
