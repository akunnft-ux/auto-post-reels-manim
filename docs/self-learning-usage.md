# Self-Learning: Panduan Penggunaan

## Alur Kerja

```
1. Login ke Facebook (personal account + Pages)
2. Buka Facebook Insights → Export data → CSV
3. Download file CSV
4. Kirim file CSV ke Telegram bot (chat yang sama)
5. Bot otomatis:
   - Deteksi file CSV
   - Parse data performa
   - Klasifikasikan post (viral/good/bad)
   - Update parameter konten (weights, hooks, CTA, hashtags)
   - Kirim notifikasi: "Self-learning selesai!"
6. Posting berikutnya akan menggunakan parameter yang sudah dioptimasi
```

## Format CSV

Bot mendukung **Facebook Insights export** (kolom otomatis terdeteksi — tidak peduli urutan atau bahasa).

**Kolom yang didukung:**
- `Post ID` / `Post Id` / `ID Posting`
- `Impressions` / `Views` / `Reach` / `Tayangan` / `Jangkauan`
- `Likes` / `Reactions` / `Suka` / `Reaksi`
- `Comments` / `Komentar`
- `Shares` / `Bagikan`

Jika format tidak dikenali, bot akan fallback menggunakan **Gemini AI** untuk parsing.

## Data yang Disimpan

| File | Isi |
|---|---|
| `data/analytics_records.json` | Semua record analytics hasil parsing CSV |
| `data/classification.json` | Klasifikasi viral/good/bad |
| `data/learning_iteration.json` | Log setiap perubahan (one-variable-at-a-time) |
| `self_learning/learning_config.json` | Konfigurasi hasil learning — dibaca main.py |

## Parameter yang Dioptimasi (Rotasi Bergilir)

1. **Content type weights** — quiz/fakta/tips (reels-matematika & reels-manim)
2. **Hook templates** — diurutkan berdasarkan engagement
3. **CTA pool** — diurutkan berdasarkan engagement
4. **Hashtag pool** — diurutkan berdasarkan frekuensi di post viral

> Setiap learning hanya mengubah **1 variabel** per iterasi, bergiliran.

## Persistence via Git

Semua perubahan di `data/*.json` dan `self_learning/learning_config.json` otomatis di-commit & push ke repo setelah setiap run GitHub Actions.

## Fallback

Jika `learning_config.json` rusak atau tidak ada, bot akan menggunakan **default hardcoded** (seperti sebelum self-learning).

## Troubleshooting

| Masalah | Solusi |
|---|---|
| CSV tidak diproses | Pastikan format CSV didukung (.csv), bukan .xlsx |
| Self-learning skipped: insufficient_data | Butuh minimal 3 record analytics untuk learning |
| Bot tidak merespon CSV | Pastikan file dikirim ke chat TELEGRAM_CHAT_ID yang benar |
