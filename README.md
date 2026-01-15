# MVoice Automation

Automasi untuk mendownload video dari TikTok/Instagram dan menganalisisnya menggunakan AI platform.

## 📁 Struktur Proyek

```
MVoice/
├── config.py          # Konfigurasi (URLs, paths, settings)
├── utils.py           # Fungsi utilitas (baca/tulis CSV, logging)
├── downloader.py      # Modul download video (bisa jalan sendiri)
├── ai_uploader.py     # Modul upload ke AI (bisa jalan sendiri)
├── pipeline.py        # Pipeline gabungan (download + AI)
├── requirements.txt   # Dependencies
├── data.csv           # Input data dengan kolom 'url'
├── output.csv         # Hasil output dengan kolom 'url' dan 'message'
└── downloads/         # Folder untuk video yang didownload
```

## 🚀 Instalasi

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install Playwright browsers:
```bash
playwright install chromium
```

## 📖 Cara Penggunaan

### 1. Download Video Saja

```bash
# Download semua video dari data.csv
python downloader.py --all

# Download URL tertentu
python downloader.py --urls "https://tiktok.com/..." "https://instagram.com/..."

# Mode headless (tanpa tampilan browser)
python downloader.py --all --headless
```

### 2. Upload ke AI Saja

```bash
# Proses semua video yang sudah didownload
python ai_uploader.py --all

# Proses satu video tertentu
python ai_uploader.py --video "downloads/tiktok_123.mp4" --url "https://..."

# Dengan custom prompt
python ai_uploader.py --all --prompt "Jelaskan pesan marketing dalam video ini"

# Mode headless
python ai_uploader.py --all --headless
```

### 3. Pipeline Lengkap (Download + AI)

```bash
# Jalankan pipeline lengkap
python pipeline.py

# Mode interaktif
python pipeline.py --interactive

# Download saja
python pipeline.py --download-only

# AI processing saja
python pipeline.py --upload-only

# Dengan custom prompt
python pipeline.py --prompt "Analisis pesan brand dalam video ini"

# Mode headless
python pipeline.py --headless
```

## ⚙️ Konfigurasi

Edit `config.py` untuk mengubah:

- `AI_URL` - URL platform AI internal
- `DEFAULT_PROMPT` - Prompt default untuk AI
- `BROWSER_HEADLESS` - True untuk mode tanpa tampilan
- `TIMEOUT` - Timeout untuk operasi browser
- `MAX_RETRIES` - Jumlah retry untuk download

## 📝 Custom Prompt

Anda bisa mengubah prompt di `config.py`:

```python
DEFAULT_PROMPT = """Analyze this video and explain:
1. Main message
2. Brand messaging
3. Key visuals
4. Target audience
"""
```

Atau gunakan parameter `--prompt` saat menjalankan:

```bash
python pipeline.py --prompt "Jelaskan pesan utama dari video ini dalam bahasa Indonesia"
```

## 📊 Output

Hasil akan disimpan di `output.csv` dengan format:

| url | message |
|-----|---------|
| https://tiktok.com/... | Hasil analisis AI... |

## 🔧 Troubleshooting

### Video tidak bisa didownload
- Pastikan URL valid dan video masih ada
- Coba jalankan tanpa mode headless untuk melihat proses
- Periksa koneksi internet

### AI tidak merespons
- Pastikan sudah login ke platform AI
- Coba tanpa mode headless untuk login manual
- Periksa apakah upload berhasil

### Error "Browser not found"
```bash
playwright install chromium
```

## 📌 Catatan

- Video yang sudah didownload akan di-skip (tidak download ulang)
- URL yang sudah diproses akan di-skip (tidak proses ulang)
- Logging tersimpan di `mvoice.log`
