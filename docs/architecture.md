# Architecture Document — Auto Post Reels Manim

## 1. Architecture Overview

Bot Python monolitik (modular dalam file tunggal) untuk generate narasi soal matematika via Gemini AI, render video animasi 1080x1920 menggunakan **Manim Community Edition**, komposit BGM via FFmpeg, dan post ke Facebook Reels via Graph API. Dijadwalkan via GitHub Actions cron 3-5x/hari. Tidak ada database server — history disimpan di JSON file.

**Perbedaan utama dari versi sebelumnya (auto-post-reels-matematika):**
- Manim CE menggantikan Pillow + MoviePy untuk rendering video
- Video memiliki animasi dinamis (bukan slideshow statis)
- Manim output MP4 langsung (tidak perlu frame compositing)
- BGM ditambahkan post-render via FFmpeg (audio mixing)
- Manim cache management diperlukan

```
+------------------------------------------------------------------+
|                     GitHub Actions (Ubuntu)                       |
|  +----------+  +----------+  +----------+                         |
|  | Cron     |  | Cron     |  | Cron     |                         |
|  | 06:00 UTC|  | 10:00 UTC|  | 13:00 UTC|                         |
|  +----+-----+  +----+-----+  +----+-----+                         |
|       +----------+----------------+                               |
|                  v                                                 |
|     +-----------------------------+                               |
|     |         main.py             |                               |
|     |  (single script bot)        |                               |
|     +--+-------+--------+--------+                               |
+--------+-------+--------+----------------------------------------+
         |       |        |
         v       v        v
   +---------+ +--------+ +----------------+
   | Gemini  | | Manim  | | Facebook       |
   | API     | | CE     | | Graph API      |
   |(narasi) | |(video) | |(post Reels)    |
   +---------+ +---+----+ +----------------+
                    |
              +-----+-----+
              |  FFmpeg   |
              |(BGM mix)  |
              +-----+-----+
                    |
              +-----+-----+
              |  history  |
              |  .json    |
              |  + audio/ |
              |  + fonts/ |
              +-----+-----+
                    | (committed back to repo)
                    v
             GitHub Repository
```

## 2. Context Diagram

```
+--------------+     +-----------------------------------------+     +--------------+
|   Admin      |     |         GitHub Actions                  |     |   Audiens    |
| (via Telegram)|--->|  +--------------+  +-------------+     |--->| (Facebook)   |
|              |     |  | Cron Trigger |  |  main.py    |     |     |              |
|              |<----|  +--------------+  +------+------+     |     |              |
+--------------+     +---------------------------+------------+     +--------------+
                                                  |
        +-----------------------------------------+--------------------------+
        |                    |                    |                         |
        v                    v                    v                         v
+---------------+  +-------------------+  +-------------------+  +------------------+
|  Gemini API   |  |  Manim CE        |  |  FFmpeg           |  | Facebook Graph   |
|  (Google)     |  |  (local render)  |  |  (BGM audio mix)  |  | API (Meta)       |
+---------------+  +-------------------+  +-------------------+  +------------------+
```

## 3. Module Architecture

Modular monolith dalam 1 file Python dengan fungsi terpisah per modul:

| Modul | Fungsi | Tanggung Jawab |
|---|---|---|
| **Narasi Generator** | `generate_narasi(topic, history, content_type)` | Panggil Gemini API dengan prompt sesuai tipe konten (quiz/fakta/tips), validasi JSON, retry logic 3x |
| **Content Strategist** | `pick_content_type()`, `get_hook_template(content_type)` | Pilih tipe konten (quiz/fakta/tips) weighted random, hook template untuk engagement |
| **Caption Builder** | `build_caption(narasi, content_type, hook_template)` | Generate caption: hook + body + CTA + hashtags; compliance check |
| **Topic Manager** | `pick_topic(history)`, `get_used_topics_today(history)` | Pilih topik unik, rotasi harian |
| **Manim Scene Renderer** | `render_scene(narasi, filename, content_type)` | Render 3-scene video animasi 1080x1920 menggunakan Manim CE; animasi berbeda per content_type |
| **Audio Compositor** | `composite_bgm(video_path, bgm_path)` | Tambah BGM ke video via FFmpeg post-render |
| **Facebook Poster** | `post_to_facebook(video_path, caption)` | Upload ke Facebook Reels, handle token expiry |
| **History Manager** | `load_history()`, `save_history()`, `is_duplicate()` | Baca/tulis/cari duplikat di history.json |
| **Compliance Checker** | `compliance_check(caption)` | Cek engagement bait pattern, BLOCK posting jika terdeteksi |
| **Error Notifier** | `notify_telegram(message)` | Kirim notifikasi error ke Telegram |
| **Orchestrator** | `main()` | Koordinasi urutan eksekusi |

### Module Dependencies

```
NarasiGenerator     --> Gemini API (external)
ContentStrategist   --> config (inline constants)
CaptionBuilder      --> NarasiGenerator (output), ContentStrategist (output)
CaptionBuilder      --> ComplianceChecker (validation)
TopicManager        --> HistoryManager (read)
ManimSceneRenderer  --> NarasiGenerator (output), fonts/
ManimSceneRenderer  --> FFmpeg (system dep), LaTeX (system dep)
AudioCompositor     --> ManimSceneRenderer (output), audio/ (local files)
AudioCompositor     --> FFmpeg (system dep)
FacebookPoster      --> AudioCompositor (output)
FacebookPoster      --> ComplianceChecker (re-run at posting time)
HistoryManager      --> FacebookPoster (save on success)
ComplianceChecker   --> references/platform-compliance.md rules
ErrorNotifier       --> Telegram API (external)
Orchestrator        --> semua modul di atas
```

## 4. Layer Architecture

| Layer | Components |
|---|---|
| **Presentation** | N/A (bot-only, no UI) |
| **Application** | `main()` — orchestrator |
| **Domain** | NarasiGenerator, TopicManager, ManimSceneRenderer, FacebookPoster, HistoryManager |
| **Infrastructure** | Gemini client, Manim CE runtime, FFmpeg subprocess, Facebook Graph client, Telegram client, File I/O |
| **Data** | history.json (file system) |

## 5. Feature Architecture

### Feature: Generate & Post Animasi Reels

| Aspek | Detail |
|---|---|
| Purpose | Satu siklus: generate -> render animasi Manim -> composite BGM -> post -> record |
| Inputs | Environment variables, history.json, fonts, BGM |
| Outputs | Video animasi di Facebook Reels, entry baru di history.json |
| Dependencies | Gemini API, Manim CE (pip), FFmpeg (system), LaTeX (system), Facebook Graph API |
| Error Handling | Retry Gemini 3x, timeout Manim 8 menit, notif Telegram jika fatal, cleanup cache + temp files |

### Feature: Manim Scene Rendering

| Aspek | Detail |
|---|---|
| Purpose | Animasi matematika dinamis 3 scene |
| Configuration | `config.pixel_width=1080, pixel_height=1920` (portrait), `quality=low_quality` (cepat), `disable_caching=true` |
| Scene 1 (5-8 dtk) | Intro animated title (content type label) + soal muncul dengan Write/FadeIn |
| Scene 2 (5-8 dtk) | 4 pilihan ganda muncul satu per satu dengan slide-in animation |
| Scene 3 (5-10 dtk) | Jawaban benar di-highlight + penjelasan animasi (Transform, Indicate) |
| Output | Raw MP4 (tanpa audio) -> siap untuk audio compositing |

### Feature: Audio Compositing (FFmpeg)

| Aspek | Detail |
|---|---|
| Purpose | Tambah BGM ke video output Manim |
| Command | `ffmpeg -i video.mp4 -i bgm.mp3 -filter_complex "[1:a]volume=0.15[a1];[0:a][a1]amix=inputs=2:duration=first" -c:v copy output.mp4` |
| Fallback | Jika BGM tidak ada atau lebih pendek dari video -> render tanpa audio |

### Feature: Anti-Duplikasi & Content Rotation

| Aspek | Detail |
|---|---|
| Purpose | Cegah soal sama, rotasi topik & content type |
| Content Type | Quiz challenge (40%), Fakta (30%), Tips (30%) — weighted random |
| Topic Rotation | 5 topik, tidak boleh sama dalam 1 hari |

## 6. Data Flow

### Main Flow (Posting Cycle)

```
main()
  |
  +- 1. Load history.json
  |
  +- 2. pick_content_type() -> content_type (quiz/fakta/tips)
  |      Rotasi: 40% quiz, 30% fakta, 30% tips
  |
  +- 3. pick_topic() -> topic_id (unik hari ini)
  |
  +- 4. get_hook_template(content_type) -> hook template
  |
  +- 5. generate_narasi(topic, history, content_type)
  |      +- Call Gemini API with content-type-specific prompt
  |      +- Parse JSON, validate fields
  |      +- Check duplicate
  |      +- Return narasi dict
  |
  +- 6. build_caption(narasi, content_type, hook)
  |      +- Hook + Body + CTA + Hashtags
  |      +- Compliance check -> BLOCK if bait detected
  |
  +- 7. render_scene(narasi, filename, content_type)
  |      +- Manim CE: 3 animated scenes (portrait 1080x1920)
  |      +- Output raw MP4
  |
  +- 8. composite_bgm(video_path, random_bgm)
  |      +- FFmpeg audio mix -> final MP4
  |
  +- 9. post_to_facebook(video_path, caption)
  |      +- Token expiry pre-check
  |      +- Compliance check (re-run at posting time)
  |      +- POST /{page_id}/videos
  |      +- Return post_id
  |
  +- 10. save_history(narasi, topic, tanggal, content_type)
  |
  +- 11. Cleanup temp files + Manim cache
```

### Failure Flow

```
Step 5 fails (Gemini 3x retry exhausted)
  -> notify_telegram("Gemini API failed")
  -> exit(1), history unchanged

Step 7 fails (Manim render error/timeout)
  -> cleanup temp + Manim cache
  -> notify_telegram("Manim render failed: {error}")
  -> exit(1)

Step 8 fails (FFmpeg audio mix error)
  -> fallback: gunakan video tanpa audio
  -> log warning, continue posting

Step 9 fails (Facebook API error)
  -> cleanup temp files
  -> notify_telegram("FB upload failed: {error}")
  -> exit(1), JANGAN simpan history
```

## 7. Integration Design

### Manim Community Edition (Local)

| Aspek | Detail |
|---|---|
| Package | `pip install manim` |
| Config | `config.pixel_width=1080, pixel_height=1920`; `quality="low_quality"`; `disable_caching=True` |
| Rendering | In-process via `tempconfig()` context manager, bukan CLI subprocess |
| Timeout | 8 menit (480 detik) — jika lebih, kill process |
| System Deps | FFmpeg (apt), LaTeX minimal (texlive-latex-base, texlive-latex-extra) |
| Error Handling | Render error -> cleanup cache, retry 1x dengan simplified scene |

### Gemini API

| Aspek | Detail |
|---|---|
| Endpoint | `POST https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent` |
| Auth | `GEMINI_API_KEY` in URL |
| Request | JSON with prompt per content type + responseMimeType: application/json |
| Retry | 3 attempts, different topic on retry |
| Timeout | 30 seconds |

### Facebook Graph API

| Aspek | Detail |
|---|---|
| Endpoint | `POST https://graph.facebook.com/v22.0/{PAGE_ID}/videos` |
| Auth | `FB_ACCESS_TOKEN` (Page Access Token) |
| Request | Multipart: video file + description + access_token |
| Pre-check | Token expiry validation before posting |
| Error Handling | 401 -> BLOCKED_TOKEN_EXPIRED, halt; 429 -> backoff; 403 -> log + human review |

### FFmpeg (Audio Compositing)

| Aspek | Detail |
|---|---|
| Type | System dependency (apt install ffmpeg) |
| Usage | Subprocess call untuk mix audio track ke video |
| Command | `ffmpeg -i video.mp4 -i bgm.mp3 -filter_complex amix=inputs=2:duration=first -c:v copy -shortest output.mp4` |
| Fallback | Jika gagal -> video tanpa audio, log warning |

### Telegram Bot API

| Aspek | Detail |
|---|---|
| Endpoint | `POST https://api.telegram.org/bot{TOKEN}/sendMessage` |
| Auth | Bot Token in URL path |
| Error Handling | Fire-and-forget (log warning, jangan blocking) |

## 8. Authorization Design

| Resource | Authentication | Authorization |
|---|---|---|
| Gemini API | API Key (env var) | N/A (single key) |
| Facebook Page | Page Access Token (env var) | Scope: pages_manage_posts |
| Telegram Chat | Bot Token + Chat ID (env vars) | N/A |
| history.json | File system (repo) | Git-tracked, no auth |

## 9. Audit Design

| Action | Data Captured | Storage |
|---|---|---|
| Post sukses | {soal, jawaban, topik, content_type, tanggal} | history.json |
| Error fatal | Timestamp + error message + step | GitHub Actions log + Telegram |
| Manim render time | Timestamp + duration + scene complexity | GitHub Actions log |
| Token expiry | Timestamp + platform | GitHub Actions log |

## 10. Observability Design

| Aspect | Implementation |
|---|---|
| Application Logs | print() with timestamp, visible di GitHub Actions |
| Manim Render Logs | Captured from Manim output (verbosity warning level) |
| Error Logs | Telegram notification + stdout |
| Execution Status | GitHub Actions workflow run status |
| Rendering Performance | Waktu render per scene dicatat di log |

## 11. Security Design

| Concern | Implementation |
|---|---|
| Secret Management | GitHub Actions encrypted secrets (5 env vars) |
| .env file | .gitignore, .env.example tanpa nilai real |
| Facebook Token | Long-lived Page Access Token, pre-emptive expiry check |
| No PII | Hanya teks soal, jawaban, topik |
| File Permissions | GitHub token scope: contents:write minimal |

## 12. Performance Strategy

| Operation | Target | Strategy |
|---|---|---|
| Gemini API call | <10s | 30s timeout, retry 3x |
| Manim rendering | <8 menit | `quality=low_quality`, scene sederhana, timeout 480s |
| FFmpeg audio mix | <30s | Copy video codec, hanya mix audio |
| Facebook upload | <30s | File <50MB, koneksi stabil |
| Total execution | <12 menit | Sequential, no parallelism |

### Manim Optimization Strategies
1. **quality="low_quality"** — 480p internal render, upscale bukan pilihan, ini untuk kecepatan
2. **disable_caching=True** — tidak simpan partial movie files
3. **frame_rate=24** — FPS rendah cukup untuk animasi teks
4. **Scene sederhana** — hindari 3D, particle effects, complex geometry
5. **Tex fallback** — jika LaTeX terlalu lambat, fallback ke Text

## 13. Scalability Strategy

| Aspect | Approach |
|---|---|
| Current scale | 3-5 posts/day |
| Growth (12mo) | Same (stable requirement) |
| History cap | 180 entries (~60 days), auto-purge |
| Manim cache | Flush per sesi — no persistent cache |
| Scaling approach | Vertical if needed (not expected) |

## 14. Deployment Architecture

```
+-------------------------------------------------------+
|              GitHub Repository                         |
|  auto-post-reels-manim/                                |
|  +- main.py                   (bot logic)             |
|  +- scenes.py                 (Manim scene classes)   |
|  +- requirements.txt          (manim, google-genai)   |
|  +- .env.example                                       |
|  +- data/history.json                                 |
|  +- fonts/*.ttf                                       |
|  +- audio/*.mp3                                       |
|  +- docs/*.md                                         |
|  +- .github/workflows/auto-post.yml                   |
+---------------------------+---------------------------+
                            | push
                            v
+-------------------------------------------------------+
|              GitHub Actions (ubuntu-latest)             |
|  +- Checkout repo                                      |
|  +- Setup Python 3.12                                  |
|  +- apt: ffmpeg, texlive-latex-base, texlive-latex-extra|
|  +- pip install manim google-genai requests            |
|  +- python main.py                                     |
|  +- git commit + push history.json                     |
+-------------------------------------------------------+
```

### Environment Variables (GitHub Secrets)

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key |
| `FB_PAGE_ID` | Facebook Page ID |
| `FB_ACCESS_TOKEN` | Facebook Page Access Token (long-lived) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token for error notif |
| `TELEGRAM_CHAT_ID` | Telegram chat ID for admin notif |

## 15. Architecture Decision Records

### ADR-001: Manim Community Edition over ManimGL (3b1b original)

| Aspek | Detail |
|---|---|
| Decision | Gunakan Manim Community Edition (`pip install manim`) |
| Reason | CE stable, headless Cairo renderer (tidak butuh OpenGL display), dokumentasi lengkap, active community. ManimGL butuh OpenGL yang sulit di headless GitHub Actions runner |
| Alternatives | ManimGL (3b1b), MoviePy + Pillow (versi sebelumnya) |
| Tradeoff | CE rendering speed mungkin sedikit lebih lambat dari GL, tapi kompatibel headless |
| Chosen | Manim CE |

### ADR-002: In-process Manim rendering via tempconfig

| Aspek | Detail |
|---|---|
| Decision | Render Manim via Python `tempconfig()` context manager, bukan CLI subprocess |
| Reason | Kontrol timeout lebih mudah, error handling dalam proses, tidak perlu parsing CLI output |
| Alternatives | CLI subprocess `manim -ql scene.py` |
| Tradeoff | Manim proses dalam thread yang sama — jika crash, bisa bawa turun script utama |
| Chosen | `tempconfig()` in-process |

### ADR-003: BGM Post-Render via FFmpeg (bukan di Manim)

| Aspek | Detail |
|---|---|
| Decision | Tambah BGM setelah Manim render via FFmpeg subprocess |
| Reason | Manim tidak punya audio mixing API native yang praktis. FFmpeg lebih cepat dan fleksibel untuk audio mixing |
| Alternatives | Manim `add_sound()` (terbatas), MoviePy audio compositing (extra dep) |
| Tradeoff | Extra step, file I/O tambahan |
| Chosen | FFmpeg audio mixing post-render |

### ADR-004: Single Python Script (Modular Functions)

| Aspek | Detail |
|---|---|
| Decision | Maintain bot as single `main.py` dengan fungsi modular, plus `scenes.py` untuk Manim scene classes |
| Reason | Manim scene classes perlu dipisah agar bisa di-test dan diorganisir per content type |
| Alternatives | Single file, multiple files per module |
| Tradeoff | 2 files lebih rapi daripada 1 file >1000 lines |
| Chosen | `main.py` + `scenes.py` |

### ADR-005: Low Quality Preset untuk Kecepatan

| Aspek | Detail |
|---|---|
| Decision | Render Manim dengan `quality="low_quality"` (480p internal) |
| Reason | Target render <8 menit. Kualitas visual yang baik untuk teks animasi. Facebook Reels compress lagi video, HD loss tidak signifikan |
| Alternatives | `medium_quality` (720p), `high_quality` (1080p) |
| Tradeoff | Sedikit loss kualitas, tapi rendering 3-4x lebih cepat |
| Chosen | `low_quality` |

### ADR-006: JSON File Instead of Database

| Aspek | Detail |
|---|---|
| Decision | `data/history.json` as persistent store |
| Reason | Max 180 records, single writer (no concurrency), git-tracked |
| Alternatives | SQLite, Supabase |
| Tradeoff | No query capability, linear scan for dedup (OK for <200 items) |
| Chosen | JSON file |

### ADR-007: GitHub Actions as Scheduler

| Aspek | Detail |
|---|---|
| Decision | GitHub Actions cron triggers |
| Reason | Free, built-in secrets, auto commit/push history |
| Alternatives | Cron di VPS, AWS Lambda |
| Tradeoff | Terbatas cron triggers, harus push history via action |
| Chosen | GitHub Actions |

## 16. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Manim CE render >8 menit | Medium | High | Low quality preset, timeout + skip, scene simplification |
| Manim CE crash/incompatible di GHA runner | Low | Critical | Test rendering di ubuntu-latest sebelum deploy |
| LaTeX install terlalu besar (>500MB) | Medium | Medium | texlive-latex-base minimal; fallback non-LaTeX |
| Manim cache penuh (partial movie files) | Medium | Medium | disable_caching=True ; flush cache post-render |
| Facebook API changes | Low | High | Versioned API |
| Facebook token 60-day expiry | Medium | Medium | Pre-emptive check; System User token |
| Gemini API rate limit | Low | Medium | Only 3-5 calls/day |
| Disk space habis (Manim output + cache) | Medium | Medium | Cleanup after render, flush cache |

## 17. Recommendations

1. **Prototype dulu** — jalankan Manim CE di GitHub Actions runner untuk validasi render time dan kompatibilitas sebelum implementasi penuh
2. **Low quality preset** — untuk kecepatan, baru naik quality setelah stabil
3. **Scene sederhana** — animasi teks + basic shapes, hindari 3D
4. **Fallback non-LaTeX** — sediakan Text fallback jika LaTeX tidak terinstall atau terlalu lambat
5. **Token pre-check** — validasi Facebook token sebelum upload
6. **Compliance BLOCK** — bukan log, lindungi akun
7. **Gradual posting ramp** — mulai 3x/hari, naik ke 5x setelah minggu 2
8. **Monitoring** — catat Manim render time di setiap run, alert jika >5 menit
