# Discovery Report — Auto Post Reels Manim

## 1. Executive Summary

Proyek ini adalah bot auto-posting untuk Facebook Reels dengan konten edukasi matematika, menggunakan **Manim** (Mathematical Animation Engine oleh 3Blue1Brown) untuk rendering video animasi, menggantikan Pillow + MoviePy yang digunakan di versi sebelumnya (`auto-post-reels-matematika`). Bot akan menghasilkan naskah soal via Gemini AI, merender video animasi matematika (15-30 detik) menggunakan Manim, dan memposting ke Facebook Reels via Graph API. Dijadwalkan via GitHub Actions cron.

## 2. Project Type Classification

| Aspek | Klasifikasi |
|---|---|
| **Jenis Proyek** | Social media growth / auto-posting bot |
| **Sub-jenis** | Konten edukasi matematika dengan animasi |
| **Stack Applicability** | Default Stack (Next.js/Supabase/Vercel) **TIDAK berlaku** — bot-only, headless |
| **Phase 4 (UI/UX)** | **Not applicable** — tidak ada dashboard/admin UI |
| **Domain Spec** | `social-media-growth-engine` — module contracts, data schema, compliance rules |

## 3. Problem Statement

Membutuhkan konten Reels edukasi matematika yang konsisten 3-5x/hari secara otomatis. Video animasi matematika bergaya 3Blue1Brown memiliki potensi engagement lebih tinggi daripada slideshow statis. Produksi manual video animasi matematika tidak scalable.

## 4. Stakeholders

| Stakeholder | Role |
|---|---|
| Pemilik akun Facebook | Admin & Operator |
| Audiens (pengikut Facebook) | End Users |

## 5. User Roles

| Role | Responsibilities |
|---|---|
| Admin | Mengatur jadwal, memonitor error via Telegram, mengelola kredensial |
| Sistem (Bot) | Generate narasi, render video animasi Manim, posting, catat history |

## 6. Core Workflows

### Workflow: Auto Post Reels (Manim)

```
GitHub Actions Cron Trigger
  ↓
Load history.json
  ↓
Pilih topik (5 topik matematika)
  ↓
Pilih content type (quiz 40%, fakta 30%, tips 30%)
  ↓
Get hook template sesuai content type
  ↓
Call Gemini API → generate narasi (soal + pilihan + jawaban + penjelasan)
  ↓
Build caption (hook + body + CTA + hashtags) → compliance check
  ↓
Render video animasi dengan Manim (1080×1920, 15-30 detik):
  - Scene 1: Soal — animasi teks soal + efek masuk
  - Scene 2: Pilihan — animasi opsi jawaban satu per satu
  - Scene 3: Pembahasan — animasi jawaban benar + penjelasan
  - Tambah BGM background
  - Output MP4 H.264
  ↓
Post ke Facebook Reels via Graph API /videos endpoint
  ↓
Simpan history ke history.json
  ↓
Commit & push history ke repo
```

### Workflow: Analytics Batch (sesi terpisah)

```
Trigger (manual atau cron harian)
  ↓
Fetch analytics via Facebook Insights API (views, likes, comments, shares)
  ↓
Record source: "api" ke analytics.json
  ↓
Fetch follower count via Graph API
  ↓
Record ke growth.json
```

### Workflow: Self-Learning Review (setiap 7 hari)

```
Load 7 hari analytics (source: "api" only)
  ↓
Classify posts: viral / good / bad (per §5.1 thresholds)
  ↓
Generate rekomendasi (1 variable at a time)
  ↓
Kirim ringkasan ke Telegram admin
```

## 7. Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | Bot harus generate narasi soal matematika via Gemini AI | MUST |
| FR-02 | Bot harus render video animasi 9:16 (1080×1920) menggunakan Manim | MUST |
| FR-03 | Bot harus posting ke Facebook Reels via Graph API | MUST |
| FR-04 | Bot harus berjalan 3-5x/hari via cron | MUST |
| FR-05 | Bot harus mencegah duplikasi soal (history.json) | MUST |
| FR-06 | Bot harus kirim notifikasi error via Telegram | MUST |
| FR-07 | Bot harus support multiple topik (5 topik) | MUST |
| FR-08 | Bot harus rotasi topik agar tidak sama dalam 1 hari | MUST |
| FR-09 | Video harus punya background music (BGM) | MUST |
| FR-10 | Video harus animasi matematika (bukan slideshow statis) | MUST |
| FR-11 | Bot harus support retry jika API gagal (3x) | SHOULD |
| FR-12 | Setiap caption harus punya hook (curiosity gap) + CTA (follow/comment) | MUST |
| FR-13 | Compliance check harus BLOCK posting jika engagement bait terdeteksi | MUST |
| FR-14 | Bot harus kumpulkan analytics post (views, likes, comments, shares) via Insights API | MUST |
| FR-15 | Bot harus track follower count harian | MUST |
| FR-16 | Self-learning loop setiap 7 hari berdasarkan data analytics (source: "api") | SHOULD |
| FR-17 | Variasi content type: quiz challenge, fakta, tips cepat | MUST |

## 8. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-01 | Durasi video | 15-30 detik |
| NFR-02 | Resolusi video | 1080×1920 (9:16 portrait) |
| NFR-03 | Eksekusi per sesi | <10 menit (Manim rendering lebih lambat) |
| NFR-04 | Error rate | <5% per bulan |
| NFR-05 | Semua dependency gratis / open source | ✓ |
| NFR-06 | History retention | Minimal 60 hari (180 entries max) |
| NFR-07 | Compliance block rate | 0 posting terlarang lolos |
| NFR-08 | Analytics source | "api" (bukan estimasi) |

## 9. Reporting Requirements

| Report | Description | Priority |
|---|---|---|
| Error notification | Telegram message saat bot gagal | MUST |
| GitHub Actions logs | Visible di dashboard GitHub Actions | SHOULD |
| Follower growth report | Daily follower count + growth rate | SHOULD |
| Weekly growth summary | Total followers, avg daily growth, best content format | SHOULD |

## 10. Integration Requirements

| Integration | Purpose | Authentication |
|---|---|---|
| Google Gemini API | Generate narasi soal | API Key |
| Facebook Graph API | Post video ke Facebook Reels | Page Access Token |
| Facebook Insights API | Ambil analytics post | Page Access Token |
| Telegram Bot API | Kirim notifikasi error | Bot Token |

## 11. Assumption Log

| # | Assumption | Reason | Impact | Status |
|---|---|---|---|---|
| A-01 | Manim dapat render 1080×1920 (portrait) dengan scene matematika pendek (15-30 detik) | Manim default output landscape, perlu konfigurasi | Critical | Inferred |
| A-02 | Manim bisa dijalankan di GitHub Actions Ubuntu runner | Manim requires python + FFmpeg + OpenGL (optional) | High | Inferred |
| A-03 | Waktu rendering Manim <8 menit per video pendek | Manim dikenal lambat untuk scene kompleks | High | Inferred |
| A-04 | Gemini bisa output JSON narasi sesuai format | Terbukti di project sebelumnya | High | Confirmed |
| A-05 | H.264 codec compatible dengan Facebook Reels | Standar industri | High | Confirmed |
| A-06 | Facebook Insights API tersedia untuk Page Access Token | Butuh scope pages_read_engagement | Medium | Inferred |
| A-07 | GitHub Actions runner cukup kuat render Manim (2-core CPU) | Manim bisa render tanpa GPU (CPU mode) | Medium | Inferred |
| A-08 | BGM bundle MP3 bebas royalti | Sama seperti project sebelumnya | Medium | Confirmed |

## 12. Gap Analysis

| Gap | Description | Action |
|---|---|---|
| Manim belum pernah dipakai di proyek ini | Perlu prototyping untuk ukur rendering time di GitHub Actions | Buat test scene sederhana dulu |
| Belum ada template scene Manim untuk 3 content type | Perlu desain scene: quiz, fakta, tips | Tentukan di arsitektur |
| Manim default output landscape (16:9) | Perlu konfigurasi portrait (9:16) | Frame.camera.frame_height/width config |
| Manim rendering time tidak pasti | Perlu benchmark untuk pastikan <10 menit | Test rendering di ubuntu-latest |
| Font dan LaTeX rendering Manim | Manim native dukung LaTeX, bagus untuk math | Manfaatkan LaTeX untuk rumus |
| Tidak ada transisi/animasi di versi lama | Manim native punya animasi — ini justru advantage | Gunakan Write, FadeIn, dll |

## 13. Open Questions

| # | Question | Answer |
|---|---|---|
| Q-01 | Apakah Manim bisa render di headless server (tanpa display)? | (Harus pakai -p flag atau --format=mp4, tidak perlu OpenGL) |
| Q-02 | Berapa estimasi waktu render per scene (15-30 detik video)? | (Perlu di-test — bisa 2-8 menit tergantung kompleksitas) |
| Q-03 | Bahasa konten? | Indonesia (sama seperti project sebelumnya) |
| Q-04 | Font tetap DejaVu Sans atau pakai LaTeX? | Manim pakai LaTeX default untuk math — sangat cocok |
| Q-05 | Perlu efek 3D atau cukup 2D animasi? | 2D cukup untuk soal matematika tingkat CPNS/TKA/SNBT |
| Q-06 | Apakah perlu Manim GL viewer atau cukup Cairo renderer? | Cairo renderer cukup untuk MP4 output |

## 14. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Manim rendering terlalu lama di GitHub Actions (>10 menit) | Medium | High | Optimasi scene, kurangi frame rate, test early |
| Manim tidak kompatibel dengan Ubuntu GitHub Actions runner | Low | High | Test di ubuntu-latest sebelum deploy |
| Manim memory usage terlalu tinggi di runner (7GB limit) | Medium | Medium | Monitor memory, optimasi scene complexity |
| Facebook Graph API berubah | Low | High | Gunakan versioned API |
| Gemini API rate limit | Low | Medium | Retry logic + backoff |
| Disk space habis di runner (Manim cache + output) | Medium | Medium | Cleanup temp files, disable Manim cache |
| Target follower growth tidak tercapai | High | High | Content strategy optimization |
| Engagement bait detection → shadow ban | Medium | Critical | Compliance check BLOCK (bukan log) |

## 15. Feature Prioritization

| Feature | Priority |
|---|---|
| Generate narasi + render video Manim + post ke Facebook | MUST |
| Rotasi topik + anti duplicate | MUST |
| Error notification Telegram | MUST |
| Background music | MUST |
| Animasi matematika (bukan slideshow statis) | MUST |
| Content type rotation (quiz/fakta/tips) | MUST |
| Hook + CTA di caption | MUST |
| Compliance check BLOCK | MUST |
| Analytics engine (Insights API, source: "api") | MUST |
| Follower growth tracking | SHOULD |
| Self-learning loop | SHOULD |
| Multiple BGM random | COULD |
| Cross-platform (TikTok/IG) | FUTURE |

## 16. Recommendation

Lanjut ke Phase 2 (PRD). Stack: **Python + Gemini + Manim + FFmpeg + Facebook Graph API + GitHub Actions**. Tidak perlu UI/UX.

**Key architectural decision**: Manim menggantikan Pillow + MoviePy sebagai rendering engine. Perlu prototyping untuk validasi performa Manim di GitHub Actions runner sebelum implementasi penuh.

Sifat proyek: **Hybrid social media bot** — bot-only (headless) dengan konten edukasi matematika. `social-media-growth-engine` module contracts berlaku sebagai domain spec (analytics source: "api", posting error matrix, compliance check).
