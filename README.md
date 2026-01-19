# MVoice Automation

Automasi untuk mendownload video dari TikTok/Instagram dan menganalisisnya menggunakan AI platform.  
Dioptimasi untuk memproses **ribuan video** dengan streaming batch pipeline.

## 📁 Struktur Proyek

```
MVoice/
├── config.py          # Konfigurasi (URLs, paths, settings)
├── utils.py           # Fungsi utilitas (baca/tulis CSV, logging)
├── downloader.py      # Modul download video (bisa jalan sendiri)
├── ai_uploader.py     # Modul upload ke AI (bisa jalan sendiri)
├── pipeline.py        # Pipeline streaming batch (download + AI)
├── requirements.txt   # Dependencies
├── data.csv           # Input data dengan kolom 'url'
├── output.csv         # Hasil output dengan kolom 'url' dan metrics
├── auth_state.json    # Session login (auto-generated)
├── mvoice.log         # Log file
└── downloads/         # Folder untuk video yang didownload
```

## 🚀 Instalasi

### Local (Windows/Mac)

```bash
# Clone atau copy project
cd MVoice

# Buat virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Server VM (Ubuntu/Debian via SSH)

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.10+
sudo apt-get install -y python3 python3-pip python3-venv

# Install virtual display (PENTING untuk non-headless mode)
sudo apt-get install -y xvfb

# Install tmux untuk long-running process
sudo apt-get install -y tmux

# Clone/copy project
cd /home/user
git clone <repo-url> MVoice
cd MVoice

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright + browser dependencies
playwright install chromium
playwright install-deps chromium
```

## 🔐 Login (Pertama Kali)

Sebelum menjalankan pipeline, login dulu untuk menyimpan session:

### Local
```bash
python ai_uploader.py --login
# Browser akan terbuka, login via Okta
# Tekan ENTER di terminal setelah login berhasil
```

### Server VM (via SSH dengan X11 forwarding)
```bash
# Dari local machine, connect dengan X11 forwarding
ssh -X user@server-ip

# Jalankan login (browser akan muncul di local)
cd MVoice
source .venv/bin/activate
python ai_uploader.py --login
```

### Atau copy auth_state.json
Jika sudah login di local, copy file `auth_state.json` ke server:
```bash
scp auth_state.json user@server-ip:/home/user/MVoice/
```

## 📖 Cara Penggunaan

### Quick Start (Local)

```bash
# Interactive mode - pilih mode via menu
python pipeline.py -i

# Full pipeline dengan default settings
python pipeline.py
```

### Jalankan di Server VM (SSH)

```bash
# 1. Connect ke server
ssh user@server-ip

# 2. Masuk ke project
cd MVoice
source .venv/bin/activate

# 3. Start tmux session (agar bisa disconnect tanpa stop proses)
tmux new -s mvoice

# 4. Jalankan dengan xvfb (virtual display)
xvfb-run python pipeline.py --batch-size 10

# 5. Detach dari tmux (proses tetap jalan)
# Tekan: Ctrl+B, lalu D

# 6. Untuk reconnect nanti:
tmux attach -t mvoice
```

## 🔄 Streaming Batch Pipeline

Pipeline dioptimasi untuk ribuan video dengan minimal disk usage:

```
┌─────────────────────────────────────────────────────┐
│ Batch 1: Download 5 video                           │
│    ↓                                                │
│ Upload video 1 → AI (1 min) → Hapus video 1        │
│ Upload video 2 → AI (1 min) → Hapus video 2        │
│ ...                                                 │
│    ↓                                                │
│ Batch 2: Download 5 video berikutnya               │
│    ↓                                                │
│ ... repeat sampai selesai ...                       │
└─────────────────────────────────────────────────────┘
```

### Command Options

```bash
# Full pipeline (default: batch 5, delete after upload)
python pipeline.py

# Custom batch size
python pipeline.py --batch-size 10

# Jangan hapus video setelah upload
python pipeline.py --no-delete

# Download saja (tanpa AI upload)
python pipeline.py --download-only --batch-size 20

# Upload saja (dari video yang sudah didownload)
python pipeline.py --upload-only

# Interactive mode
python pipeline.py -i

# Headless mode (experimental, mungkin kena bot detection)
python pipeline.py --headless
```

### Untuk Server VM (Recommended)

```bash
# Start tmux + run dengan xvfb
tmux new -s mvoice
xvfb-run python pipeline.py --batch-size 10

# Atau one-liner
tmux new -d -s mvoice 'cd /home/user/MVoice && source .venv/bin/activate && xvfb-run python pipeline.py --batch-size 10'
```

## 📥 Download Video Saja

```bash
# Download semua video dari data.csv
python downloader.py --all

# Download URL tertentu
python downloader.py --urls "https://tiktok.com/..." "https://instagram.com/..."

# Di server VM
xvfb-run python downloader.py --all
```

## 🤖 Upload ke AI Saja

```bash
# Login pertama kali
python ai_uploader.py --login

# Proses semua video yang sudah didownload
python ai_uploader.py --all

# Proses satu video tertentu
python ai_uploader.py --video "downloads/tiktok_123.mp4" --url "https://..."

# Dengan custom prompt
python ai_uploader.py --all --prompt "Jelaskan pesan marketing dalam video ini"

# Clear session (logout)
python ai_uploader.py --clear-session
```

## ⚙️ Konfigurasi

Edit `config.py` untuk mengubah settings:

```python
# Browser settings
BROWSER_HEADLESS = False  # True untuk headless (tidak recommended)
SLOW_MO = 100             # Delay antar aksi (ms)
TIMEOUT = 60000           # Timeout operasi (ms)

# Download settings
MAX_RETRIES = 3           # Retry jika gagal download
DOWNLOAD_TIMEOUT = 120    # Timeout download (detik)
BATCH_SIZE = 5            # Jumlah video per batch
DELETE_AFTER_UPLOAD = True  # Hapus video setelah sukses upload

# AI Platform
AI_URL = "https://imagine.wpp.ai/chat/..."
DEFAULT_PROMPT = """..."""
```

## 📊 Input/Output

### Input: `data.csv`
```csv
url
https://www.tiktok.com/@user/video/123456
https://www.instagram.com/p/ABC123
...
```

### Output: `output.csv`
```csv
url,Business Unit,Category,Brand,Platform,Creative Link,...
https://tiktok.com/...,Beauty,Skincare,Dove,TikTok,...
```

## 🖥️ Monitoring di Server

### Check status
```bash
# List tmux sessions
tmux ls

# Attach ke session
tmux attach -t mvoice

# Lihat log real-time
tail -f mvoice.log
```

### Check progress
```bash
# Hitung video yang sudah diproses
wc -l output.csv

# Hitung video yang tersisa
wc -l data.csv
```

### Stop pipeline
```bash
# Attach ke tmux
tmux attach -t mvoice

# Stop dengan Ctrl+C

# Atau kill session
tmux kill-session -t mvoice
```

## 🔧 Troubleshooting

### Video tidak bisa didownload
- Pastikan URL valid dan video masih ada
- Coba jalankan tanpa xvfb dulu untuk debug
- Situs downloader mungkin berubah/down

### Error "Display not found" di server
```bash
# Pastikan xvfb terinstall
sudo apt-get install -y xvfb

# Jalankan dengan xvfb-run
xvfb-run python pipeline.py
```

### Session expired
```bash
# Re-login (perlu X11 forwarding atau copy dari local)
ssh -X user@server
python ai_uploader.py --login

# Atau clear dan login ulang
python ai_uploader.py --clear-session
python ai_uploader.py --login
```

### Browser not found
```bash
playwright install chromium
playwright install-deps chromium  # Linux: install system deps
```

### Out of disk space
- Pastikan `DELETE_AFTER_UPLOAD = True` di config.py
- Atau jalankan dengan `--no-delete` hanya jika disk cukup

### Process terputus
Pipeline mendukung **resume otomatis**:
- URL yang sudah diproses (ada di output.csv) akan di-skip
- Video yang sudah didownload akan di-skip
- Jalankan ulang pipeline, akan lanjut dari terakhir

## 📌 Tips untuk Ribuan Video

1. **Batch size**: Gunakan 5-10 untuk balance antara speed dan stability
2. **Monitoring**: Jalankan di tmux agar bisa disconnect SSH
3. **Disk space**: Aktifkan delete after upload (default)
4. **Rate limiting**: Pipeline sudah ada delay antar request
5. **Resume**: Jika error, jalankan ulang - akan skip yang sudah selesai

## 📝 Example Workflow (1000 videos)

```bash
# 1. Prepare data.csv dengan 1000 URLs

# 2. Login sekali di local
python ai_uploader.py --login

# 3. Copy session ke server
scp auth_state.json user@server:/home/user/MVoice/

# 4. SSH ke server
ssh user@server
cd MVoice
source .venv/bin/activate

# 5. Start tmux
tmux new -s mvoice

# 6. Run pipeline
xvfb-run python pipeline.py --batch-size 10

# 7. Detach (Ctrl+B, D) - proses tetap jalan

# 8. Check progress kapanpun
tmux attach -t mvoice

# 9. Results di output.csv
```

## 📄 License

Internal use only.

## 📦 One-line VM setup & easy run (for non-technical users)

This repo includes helper scripts to make VM setup and running the pipeline simple.

- After cloning the repo on the server, run the bootstrap script which installs system packages, creates a Python virtualenv, installs Python dependencies, and installs Playwright browsers.

One-line example (run in SSH session on the VM):

If the VM may not have `git` installed, run this (will install `git` first):

```bash
sudo apt-get update && sudo apt-get install -y git && \
	git clone https://github.com/fathindifa26/mvoice.git && cd mvoice && sudo bash bootstrap.sh
```

If `git` is already installed, this shorter command also works:

```bash
git clone https://github.com/fathindifa26/mvoice.git && cd mvoice && sudo bash bootstrap.sh
```

Notes:
- The `bootstrap.sh` will finish by checking for two required files: `auth_state.json` and `data.csv`.
- You MUST upload these two files into the project folder on the VM before running the pipeline.

How to upload the two required files from your local machine:

```bash
# From your local machine (replace user@server and path)
scp auth_state.json data.csv user@server:/home/user/mvoice/
```

After the files are uploaded, start the pipeline with the helper script:

```bash
# Start pipeline in a detached tmux session (default batch size 10)
./run_pipeline.sh --batch-size 10

# To run headless or change options
./run_pipeline.sh --batch-size 20 --headless --no-delete
```

Tips for non-technical users:
- If you need to watch logs or interact, attach to the tmux session:

```bash
tmux attach -t mvoice
```

- To stop, attach and press Ctrl+C, or kill the tmux session from another shell:

```bash
tmux kill-session -t mvoice
```

