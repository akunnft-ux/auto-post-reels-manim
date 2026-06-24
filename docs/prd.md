# Product Requirements Document — Auto Post Reels Manim

## Document Control

### Document Version History
| Version | Date | Author | Summary of Changes |
|---|---|---|---|
| 0.1 | 2026-06-24 | Tech Lead | Initial draft |

### Approval / Sign-off
| Role | Name | Status | Date |
|---|---|---|---|
| Business Owner | TBD | Pending | |
| Technical Lead | TBD | Pending | |
| Security Reviewer | TBD | Pending | |

---

## 1. Executive Summary

**Project Name:** Auto Post Reels Manim

**Project Overview:** Bot otomatis yang menghasilkan dan memposting video Reels animasi matematika ke Facebook Page menggunakan **Manim Community Edition** sebagai rendering engine. Setiap video berisi soal matematika bergaya CPNS/TKA/SNBT dengan animasi interaktif (bukan slideshow statis), dilengkapi pilihan ganda dan pembahasan animasi, durasi 15-30 detik dengan background music. Bot berjalan 3-5x/hari menggunakan GitHub Actions scheduler.

**Business Problem:** Video animasi matematika bergaya 3Blue1Brown memiliki potensi engagement jauh lebih tinggi daripada slideshow statis. Produksi manual video animasi matematika memakan waktu dan tidak scalable untuk jadwal 3-5x/hari.

**Target Users:** Pengikut Facebook Page yang mencari konten edukasi matematika animatif untuk persiapan CPNS/TKA/SNBT.

**Expected Outcomes:** 90-150 video animasi matematika terposting otomatis per bulan, pertumbuhan followers via konten engaging, audiens terbantu dengan visualisasi matematika interaktif.

**Success Definition:** Bot berjalan 3-5x/hari tanpa intervensi manual, video animasi sukses terposting ke Facebook Reels, rendering Manim selesai <10 menit per video, error rate <5% per bulan, tidak ada pelanggaran platform policy.

---

## 2. Business Objectives

| ID | Objective | Type | Success Metric |
|---|---|---|---|
| BO-001 | Mengotomatisasi produksi konten Reels animasi matematika | Primary | 90-150 video/bulan tanpa campur tangan manual |
| BO-002 | Menjaga konsistensi posting 3-5x/hari | Operational | 100% jadwal terpenuhi setiap hari |
| BO-003 | Menghindari duplikasi konten | Operational | Tidak ada soal yang sama dalam 60 hari |
| BO-004 | Meminimalkan biaya operasional | Strategic | Semua komponen gratis/open source |
| BO-005 | Notifikasi error real-time ke admin | Secondary | Admin tahu dalam <5 menit jika bot gagal |
| BO-006 | Manim rendering <10 menit per video | Operational | 100% run selesai dalam <10 menit |
| BO-007 | Zero platform policy violation | Operational | 0 banned/suspended/demoed content |

---

## 3. Project Scope

### In Scope
- Generate narasi soal matematika via Gemini AI (5 topik, 3 content type)
- Render video animasi matematika 1080x1920 portrait 15-30 detik menggunakan **Manim Community Edition**
- Animasi matematika dinamis (bukan slideshow statis): soal, pilihan, pembahasan dengan efek transisi
- Background music pada video
- Posting ke Facebook Reels via Graph API
- Scheduling 3-5x/hari via GitHub Actions cron
- History anti-duplikat berbasis JSON
- Rotasi topik harian + rotasi content type (quiz/fakta/tips)
- Notifikasi error via Telegram
- Retry logic untuk Gemini API (3x)
- Compliance check dan block pada caption
- Manim cache management dan cleanup

### Out of Scope
- Dashboard admin / UI
- Multi-platform (TikTok, Instagram, YouTube Shorts)
- User-generated content
- Komentar/feedback loop manual
- Paid ads / boosting

### Future Scope
- Cross-platform posting (Instagram, TikTok)
- Dashboard monitoring
- Voiceover AI
- Scene complexity adjustment berdasarkan performa rendering

---

## 4. Stakeholders

| Stakeholder | Responsibilities | Expectations | Success Criteria |
|---|---|---|---|
| Admin (Pemilik Akun) | Setup kredensial, monitor error, maintain bot | Bot berjalan tanpa intervensi | Tidak perlu touch bot >1 minggu |
| Audiens (Pengikut FB) | Menonton, belajar, berinteraksi | Konten animasi berkualitas, terjadwal | Engagement konsisten |
| Sistem (GitHub Actions) | Eksekusi script sesuai cron | 100% jadwal terpenuhi | No failed runs karena infrastruktur |

---

## 5. User Roles

| Role | Responsibilities | Permissions | Restrictions | Approval Authority | Reporting Access | Data Access Scope |
|---|---|---|---|---|---|---|
| Admin | Setup env vars, monitor Telegram, maintain | Manage secrets, trigger manual workflow | Cannot modify code via UI | N/A | GitHub Actions logs, Telegram | Full access to history.json |
| Bot (System) | Generate, render (Manim), post, record history | Read Gemini, write to FB, read/write history, run Manim | Cannot modify secrets | N/A | N/A | history.json, temp files only |

---

## 6. Assumption Log

| ID | Description | Reason | Impact | Status | Linked Risk |
|---|---|---|---|---|---|
| ASM-001 | Manim Community Edition dapat render 1080x1920 portrait tanpa OpenGL/display di GitHub Actions runner | Cairo renderer tersedia untuk headless | Critical | Inferred | RISK-001 |
| ASM-002 | Manim Community Edition rendering time <8 menit untuk scene matematika sederhana (15-30 detik video) | Scene complexity rendah (2D, LaTeX teks, basic shapes) | High | Inferred | RISK-002 |
| ASM-003 | GitHub Actions Ubuntu runner (2-core, 7GB RAM) cukup untuk Manim rendering | Manim menggunakan CPU untuk Cairo renderer | High | Inferred | RISK-003 |
| ASM-004 | H.264 video codec output Manim compatible dengan Facebook Reels | Manim output default MP4 H.264 | High | Confirmed | |
| ASM-005 | Facebook Graph API `/videos` endpoint mendukung upload Reels | Dokumentasi Meta | Critical | Inferred | RISK-004 |
| ASM-006 | Gemini bisa output JSON narasi sesuai format | Terbukti di project sebelumnya | High | Confirmed | |
| ASM-007 | BGM bundle MP3 bebas royalti aman untuk konten edukasi | Sama seperti project sebelumnya | Medium | Confirmed | |
| ASM-008 | Manim cache dapat di-flush per sesi untuk hemat disk | Manim config disable_caching | Medium | Inferred | RISK-005 |
| ASM-009 | LaTeX tersedia di GitHub Actions Ubuntu runner | apt install texlive-latex-base | Medium | Inferred | RISK-006 |

---

## 7. User Stories

| ID | As a | I want | So that | Realized By |
|---|---|---|---|---|
| US-001 | Admin | Bot otomatis generate soal + animasi + post | Saya tidak perlu membuat konten manual | FR-001, FR-002, FR-003 |
| US-002 | Admin | Bot tidak post soal yang sama | Konten tetap fresh untuk audiens | FR-005 |
| US-003 | Admin | Notifikasi jika bot gagal | Saya bisa segera troubleshoot | FR-006 |
| US-004 | Admin | Topik dan content type berganti setiap sesi | Variasi konten setiap hari | FR-007, FR-008 |
| US-005 | Audiens | Video animasi matematika dengan soal dan pembahasan | Belajar matematika dengan visualisasi menarik | FR-009, FR-010, FR-017 |

---

## 8. Functional Requirements

### FR-001: Generate Narasi Soal (Core)

| Field | Value |
|---|---|
| Description | Bot memanggil Gemini API untuk menghasilkan narasi soal matematika dalam format JSON |
| Business Purpose | Konten dibuat oleh AI, bukan manual |
| Traces to | BO-001 |
| Inputs | Topic ID, content type, last 20 history items |
| Outputs | JSON: {soal, pilihan[4], jawaban, penjelasan} |
| Validation Rules | Semua field wajib ada; jawaban harus salah satu dari pilihan; soal tidak duplicate; 4 pilihan valid |
| Permissions | GEMINI_API_KEY dari env var |
| Error Handling | Retry 3x dengan topic/content_type berbeda; jika semua gagal -> Telegram notif + exit |
| Acceptance Criteria | AC-001 |
| Dependencies | GEMINI_API_KEY environment variable |

Edge cases:
- EC-001: Gemini return JSON tidak valid -> retry
- EC-002: Gemini return soal duplicate -> retry
- EC-003: Gemini API timeout -> retry dengan exponential backoff
- EC-004: Semua topik sudah terpakai hari ini -> reset pool

### FR-002: Render Video Animasi dengan Manim (Core)

| Field | Value |
|---|---|
| Description | Render video animasi matematika 1080x1920 menggunakan Manim Community Edition. Video bukan slideshow statis — setiap elemen muncul dengan animasi (Write, FadeIn, Transform, dll) |
| Business Purpose | Mengubah teks jadi visual animasi yang engaging |
| Traces to | BO-001, BO-006 |
| Inputs | Narasi JSON (FR-001 output), font files, BGM file |
| Outputs | File video MP4 (H.264, 1080x1920, 15-30 detik, 24 FPS) |
| Validation Rules | File video harus ada dan tidak corrupt; durasi antara 15-30 detik; resolusi 1080x1920 |
| Permissions | Write access ke folder temp/output |
| Error Handling | Jika render gagal -> Telegram notif; cleanup temp files + Manim cache |
| Acceptance Criteria | AC-002 |
| Dependencies | Manim CE, FFmpeg, LaTeX (texlive-latex-base), fonts/ |

Edge cases:
- EC-005: Manim rendering terlalu lama (>8 menit) -> timeout, skip sesi
- EC-006: LaTeX tidak terinstall -> error handling, fallback ke Text (non-LaTeX)
- EC-007: BGM file corrupt -> render tanpa audio
- EC-008: Disk space habis saat render (Manim cache besar) -> flush cache + cleanup + error notif

### FR-003: Post ke Facebook Reels (Core)

| Field | Value |
|---|---|
| Description | Upload video ke Facebook Page sebagai Reels via Graph API |
| Business Purpose | Mempublikasikan konten ke audiens |
| Traces to | BO-001 |
| Inputs | Video MP4 file, caption text |
| Outputs | Facebook API response (post ID) |
| Validation Rules | File size <100MB; durasi 15-30 detik; format H.264 |
| Permissions | FB_PAGE_ID, FB_ACCESS_TOKEN dengan scope pages_manage_posts |
| Error Handling | Jika upload gagal -> Telegram notif; jangan simpan history jika gagal |
| Acceptance Criteria | AC-003 |
| Dependencies | FB_PAGE_ID, FB_ACCESS_TOKEN |

Edge cases:
- EC-009: Token expired (401) -> Telegram notif, jangan simpan history
- EC-010: Video format tidak didukung -> log error detail
- EC-011: Rate limit Facebook API -> exponential backoff
- EC-012: Network failure saat upload -> retry 1x, lalu fail

### FR-004: Scheduling 3-5x/Hari (Core)

| Field | Value |
|---|---|
| Description | GitHub Actions cron triggers bot sesuai jadwal |
| Business Purpose | Posting konsisten setiap hari |
| Traces to | BO-002 |
| Inputs | None (trigger-based) |
| Outputs | Bot execution |
| Validation Rules | Setiap trigger harus menjalankan 1 siklus penuh |
| Permissions | GitHub Actions workflow permissions: contents: write |
| Error Handling | Jika satu sesi gagal, sesi berikutnya tetap jalan |
| Acceptance Criteria | AC-004 |
| Dependencies | GitHub Actions, repository push access |

### FR-005: Anti-duplikasi Soal (Core)

| Field | Value |
|---|---|
| Description | Mencegah soal yang sama dipost dalam 60 hari menggunakan history.json |
| Business Purpose | Konten tetap fresh, tidak membosankan |
| Traces to | BO-003 |
| Inputs | history.json, soal baru |
| Outputs | Boolean: duplicate or not |
| Validation Rules | Exact string match terhadap seluruh history |
| Permissions | Read/write ke data/history.json |
| Error Handling | Jika file corrupt -> backup + reset |
| Acceptance Criteria | AC-005 |
| Dependencies | None |

### FR-006: Notifikasi Error Telegram (Supporting)

| Field | Value |
|---|---|
| Description | Kirim pesan ke Telegram chat saat bot mengalami error fatal |
| Business Purpose | Admin bisa segera merespon masalah |
| Traces to | BO-005 |
| Inputs | Error message string |
| Outputs | Telegram message |
| Validation Rules | Message harus mengandung timestamp + error detail |
| Permissions | TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID |
| Error Handling | Jika Telegram gagal -> log ke stdout (fire-and-forget) |
| Acceptance Criteria | AC-006 |
| Dependencies | TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID |

### FR-007: Multiple Content Type (Core)

| Field | Value |
|---|---|
| Description | 3 content type: quiz challenge (40%), fakta matematika (30%), tips cepat (30%). Masing-masing memiliki layout animasi dan prompt Gemini berbeda |
| Business Purpose | Variasi konten meningkatkan shareability dan follow conversion |
| Traces to | BO-001 |
| Inputs | Content type list (hardcoded, config-driven) |
| Outputs | Selected content type + scene template |
| Validation Rules | Content type harus dari daftar valid |
| Permissions | None |
| Error Handling | Jika content type tidak dikenal -> fallback quiz |
| Acceptance Criteria | AC-007 |
| Dependencies | FR-001, FR-002 |

### FR-008: Rotasi Topik Harian (Supporting)

| Field | Value |
|---|---|
| Description | Tidak boleh topik yang sama dalam 1 hari |
| Business Purpose | Variasi harian |
| Traces to | BO-002 |
| Inputs | history.json (topik + tanggal) |
| Outputs | Unique topic for this session |
| Validation Rules | Topic belum pernah dipakai hari ini |
| Permissions | Read history.json |
| Error Handling | Jika semua topik sudah terpakai -> reset (allow repeat) |
| Acceptance Criteria | AC-008 |
| Dependencies | FR-007 |

### FR-009: Background Music (Supporting)

| Field | Value |
|---|---|
| Description | Video memiliki BGM dari file MP3 yang di-bundle, digabung pasca-render |
| Business Purpose | Meningkatkan engagement dan watch time |
| Traces to | BO-001 |
| Inputs | MP3 file from audio/ directory |
| Outputs | Video dengan audio track |
| Validation Rules | Audio harus ada di output video |
| Permissions | Read audio/ |
| Error Handling | Jika file audio tidak ada -> render tanpa audio |
| Acceptance Criteria | AC-009 |
| Dependencies | audio/*.mp3, FFmpeg (audio mixing) |

### FR-010: Scene Layout Animasi Matematika (Core)

| Field | Value |
|---|---|
| Description | Video Manim terdiri dari scene animasi: intro soal (dengan efek Write/FadeIn), animasi pilihan ganda (muncul satu per satu dengan slide-in), dan pembahasan (highlight jawaban benar + animasi penjelasan) |
| Business Purpose | Informasi tersaji secara bertahap dengan visual engaging, bukan slideshow statis |
| Traces to | BO-001 |
| Inputs | Narasi JSON, content_type (quiz/fakta/tips) |
| Outputs | Manim Scene dengan animasi teks, shape, dan transisi |
| Validation Rules | Setiap scene harus memiliki minimal 1 animasi (bukan static frame); durasi per scene 5-10 detik |
| Permissions | None |
| Error Handling | Jika scene terlalu kompleks -> fallback ke simplified scene |
| Acceptance Criteria | AC-010 |
| Dependencies | FR-002 |

Edge cases:
- EC-013: Teks soal terlalu panjang untuk satu scene -> auto-scroll atau split scene
- EC-014: LaTeX rendering error -> fallback ke Text biasa

### FR-011: Content Hook & CTA (Core)

| Field | Value |
|---|---|
| Description | Setiap caption harus memiliki hook (1-2 kalimat curiosity gap) dan CTA (ajakan follow/comment) |
| Business Purpose | Meningkatkan view-to-follow conversion rate |
| Traces to | BO-001 |
| Inputs | Narasi JSON (soal, jawaban, penjelasan, topik) |
| Outputs | Caption dengan hook + body + CTA + hashtags |
| Validation Rules | Hook harus create curiosity gap; CTA must be compliance-approved; maksimal 6 kalimat total caption |
| Permissions | None |
| Error Handling | Jika compliance check gagal -> block posting + log; fallback ke template safe |
| Acceptance Criteria | AC-011 |
| Dependencies | Compliance check (FR-013) |

Edge cases:
- EC-015: Hook terlalu clickbaity -> compliance check reject
- EC-016: CTA terdeteksi sebagai engagement bait -> ganti dengan CTA safe alternatif

### FR-012: Manim Cache & Performance Management (Supporting)

| Field | Value |
|---|---|
| Description | Manim partial movie cache harus di-flush setiap sesi untuk menghemat disk space. Konfigurasi Manim: disable_caching=true, quality=low_quality untuk rendering cepat |
| Business Purpose | Menjaga rendering time <10 menit dan disk usage rendah |
| Traces to | BO-006 |
| Inputs | None |
| Outputs | Manim configuration |
| Validation Rules | Cache directory harus kosong setelah sesi selesai |
| Permissions | Write access ke temp directory |
| Error Handling | Jika cache tidak bisa dihapus -> log warning |
| Acceptance Criteria | AC-012 |
| Dependencies | FR-002 |

### FR-013: Compliance Check — Block on Violation (Core)

| Field | Value |
|---|---|
| Description | Compliance check HARUS block posting jika engagement bait pattern terdeteksi, bukan hanya log warning |
| Business Purpose | Mencegah banned akibat engagement bait atau policy violation |
| Traces to | BO-007 |
| Inputs | Caption text |
| Outputs | Pass -> proceed; Fail -> block posting + log + notify admin |
| Validation Rules | Cek terhadap disallowed patterns: "comment X if Y", "tag 5 friends", "share this", vote-baiting |
| Permissions | None |
| Error Handling | Blocked post -> Telegram notif + skip session (jangan simpan history) |
| Acceptance Criteria | AC-013 |
| Dependencies | None |

### FR-014: Label Content Type di Video & Caption (Supporting)

| Field | Value |
|---|---|
| Description | Setiap video menampilkan label content type di scene pertama (QUIZ CHALLENGE / FAKTA MATEMATIKA / TIPS CEPAT) dengan animasi berbeda. Caption juga menyertakan label ini |
| Business Purpose | Branding dan ekspektasi audiens |
| Traces to | BO-001 |
| Inputs | Content type dari FR-007 |
| Outputs | Animated title scene |
| Validation Rules | Label harus muncul di scene 1 |
| Permissions | None |
| Error Handling | Jika label tidak digenerate -> skip |
| Acceptance Criteria | AC-014 |
| Dependencies | FR-007, FR-010 |

---

## 9. Non-Functional Requirements

| ID | Requirement | Target | Measurement | Traces to |
|---|---|---|---|---|
| NFR-001 | Durasi video | 15-30 detik | MoviePy/ffprobe duration check | BO-001 |
| NFR-002 | Resolusi video | 1080x1920 (9:16 portrait) | ffprobe check | BO-001 |
| NFR-003 | Manim rendering time | <8 menit per scene | Timing dalam script | BO-006 |
| NFR-004 | Total eksekusi per sesi | <12 menit | GitHub Actions duration | BO-006 |
| NFR-005 | Error rate | <5% per bulan | Log analysis | BO-005 |
| NFR-006 | Gratis/open source | 0 biaya lisensi | Dependency audit | BO-004 |
| NFR-007 | History retention | Minimal 60 hari | history.json length cap | BO-003 |
| NFR-008 | Compliance block rate | 0 posting terlarang lolos | Audit log compliance_check | BO-007 |

---

## 10. Data Requirements

### Entity: Video Record
| Field | Type | Required | Description |
|---|---|---|---|
| soal | String | Yes | Teks soal matematika |
| pilihan | String[] | Yes | 4 pilihan jawaban |
| jawaban | String | Yes | Jawaban benar |
| penjelasan | String | Yes | Pembahasan jawaban |
| topik | String | Yes | Topic ID |
| content_type | String | Yes | quiz/fakta/tips |
| tanggal | Date | Yes | Tanggal post (YYYY-MM-DD) |

### Entity: History Entry
| Field | Type | Required | Description |
|---|---|---|---|
| soal | String | Yes | Teks soal (used for dedup) |
| jawaban | String | Yes | Jawaban benar |
| topik | String | Yes | Topic ID |
| content_type | String | Yes | quiz/fakta/tips |
| tanggal | String | Yes | Tanggal post |

### Entity: Post Record
| Field | Type | Required | Description |
|---|---|---|---|
| id | String | Yes | UUID |
| content_id | String | Yes | Reference to content |
| platform | String | Yes | "facebook" |
| scheduled_at | ISO8601 | Yes | Scheduled time |
| published_at | ISO8601 | No | Actual publish time |
| status | String | Yes | scheduled/published/blocked/error |
| platform_post_id | String | No | Facebook post ID |

---

## 11. Database Requirements

No database server. Single JSON file (`data/history.json`) sebagai persistent store. Sama dengan project sebelumnya.

### Entities
**history_entry**
- soal: string (unique dalam file)
- jawaban: string
- topik: string (enum: 5 topics)
- content_type: string (enum: quiz/fakta/tips)
- tanggal: string (YYYY-MM-DD)

### Constraints
- Array max 180 items
- Tidak ada foreign key (single file)
- Tidak ada index (linear scan untuk dedup, array <200 items)

---

## 12. ERD (Text)

```
[Gemini API] -- narasi JSON --> [main.py]
                                    |
                            +-------++--------+
                            |                |
                     [Manim CE]         [Post Process]
                     render scene       add BGM via FFmpeg
                     animasi math       -> MP4 final
                            |                |
                            +-------+--------+
                                    |
                            [Facebook Graph API]
                            POST /{page_id}/videos
                                    |
                            history.json (simpan)
```

---

## 13. Business Rules

| Rule | Description |
|---|---|
| BR-01 | Satu eksekusi = satu soal = satu video = satu post |
| BR-02 | Topik tidak boleh sama dalam 1 hari (kecuali pool habis) |
| BR-03 | Soal tidak boleh duplikat terhadap seluruh history |
| BR-04 | History dipotong ke 180 item saat nambah entry baru |
| BR-05 | Jika post gagal, jangan simpan history |
| BR-06 | Jika Gemini gagal 3x, skip sesi, notifikasi admin |
| BR-07 | Jika Manim rendering >8 menit, timeout, skip sesi |
| BR-08 | File temporary + Manim cache dihapus setelah selesai (sukses/gagal) |
| BR-09 | Content type rotasi: quiz 40%, fakta 30%, tips 30% |
| BR-10 | Compliance check WAJIB block (bukan log) |

---

## 14. Workflows

### Main Flow: Auto Post Reels (Manim)

```
Start (GitHub Actions trigger)
  |
 1. Load history.json -> history list
  |
 2. Pick content type (quiz/fakta/tips) weighted random
  |
 3. Pick unique topic untuk hari ini
  |
 4. Get hook template sesuai content type
  |
 5. Call Gemini API -> generate narasi soal (JSON)
  |       retry 3x jika gagal
  |
 6. Validasi narasi (field lengkap, no duplicate)
  |
 7. Build caption (hook + body + CTA + hashtags)
  |       -> compliance check -> BLOCK jika fail
  |
 8. Render scene Manim 1080x1920:
    Scene 1 (5-8 dtk): Animated intro + soal (Write, FadeIn)
    Scene 2 (5-8 dtk): Animated pilihan ganda (slide-in per opsi)
    Scene 3 (5-10 dtk): Animated jawaban + pembahasan (highlight, transform)
    -> Output raw video (no audio yet)
  |
 9. Composite BGM dengan FFmpeg (audio mixing post-render)
  |
10. Post video ke Facebook Reels via Graph API
  |
11. Simpan {soal, jawaban, topik, content_type, tanggal} ke history.json
  |
12. Cleanup temp files + Manim cache
  |
End (GitHub Actions commit + push history.json)
```

### Alternate Flow: Skip Sesi
```
Step 5 gagal 3x -> Telegram notif -> exit -> history unchanged
Step 8 timeout/error -> cleanup cache -> Telegram notif -> exit
Step 10 gagal -> Telegram notif -> exit -> history unchanged
```

### Failure Flow: Total Failure
```
Gemini fail + retry habis -> Telegram notif -> exit code 1
Manim render fail -> cleanup cache + temp -> Telegram notif -> exit code 1
Upload fail -> cleanup -> Telegram notif -> exit code 1
```

---

## 15. API Requirements

| ID | Method | Path | Purpose | Auth | Rate Limit |
|---|---|---|---|---|---|
| API-001 | POST | https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent | Generate narasi soal | API Key | 60 RPM (free tier) |
| API-002 | POST | https://graph.facebook.com/v22.0/{FB_PAGE_ID}/videos | Upload video Reels | Page Access Token | 200 calls/6h/user |
| API-003 | POST | https://api.telegram.org/bot{TOKEN}/sendMessage | Kirim notifikasi error | Bot Token | 30 msg/sec |

### API-001 Request
```json
{"contents": [{"parts": [{"text": "prompt..."}]}], "generationConfig": {"responseMimeType": "application/json"}}
```
### API-001 Response
```json
{"soal": "...", "pilihan": ["A. ...", "B. ...", "C. ...", "D. ..."], "jawaban": "A. ...", "penjelasan": "..."}
```

---

## 16. Integration Requirements

| Integration | Purpose | Trigger | Data Flow | Failure Handling |
|---|---|---|---|---|
| Google Gemini | Generate narasi soal | Step 5 workflow | prompt -> JSON | Retry 3x, then skip + notif |
| Manim CE | Render video animasi | Step 8 workflow | narasi JSON -> MP4 | Timeout 8 menit, cleanup, notif |
| Facebook Graph | Upload video Reels | Step 10 workflow | video + caption -> post ID | Notif admin, jangan simpan history |
| Telegram Bot | Error notification | Any failure | error msg -> chat | Fire-and-forget |

---

## 17. UI Requirements

N/A — Bot-only project. Tidak ada user interface.

---

## 18. Reporting Requirements

| Report | Description | Trigger | Method |
|---|---|---|---|
| Error Report | Error message + timestamp | Setiap error fatal | Telegram message |
| Execution Log | Full log each run | Setiap eksekusi | GitHub Actions log |
| Rendering Time Report | Manim rendering duration | Setiap render | GitHub Actions log + stdout |

---

## 19. Notification Requirements

| Notification | Trigger | Recipient | Content | Failure Handling |
|---|---|---|---|---|
| Error Telegram | Bot gagal eksekusi | Admin (Chat ID) | `[ERROR] YYYY-MM-DD HH:MM:SS - {error_message}` | Log to stdout |

---

## 20. Audit Requirements

| Audited Action | Data Captured | Retention |
|---|---|---|
| Setiap post sukses | {soal, jawaban, topik, content_type, tanggal} | 60 hari (history.json) |
| Setiap error | Timestamp + error message | GitHub Actions logs (90 hari) |
| History mutation | File commit di git | Forever (git history) |
| Manim rendering time | Timestamp + duration | GitHub Actions log |

---

## 21. Security Requirements

| Requirement | Implementation |
|---|---|
| Authentication | GitHub Actions secrets (5 env vars) |
| Credential Storage | GitHub encrypted secrets, never in code |
| API Key Protection | Env var only, .gitignore untuk .env |
| Facebook Token | Minimum scope: pages_manage_posts |
| No PII stored | Hanya teks soal, jawaban, topik |
| Git exposure | .env example tanpa nilai real |

---

## 22. Performance Requirements

| Metric | Target |
|---|---|
| Gemini API call | <10 detik |
| Manim scene rendering | <8 menit |
| FFmpeg audio mixing | <30 detik |
| Facebook upload | <30 detik |
| Total execution | <12 menit |
| Script startup | <5 detik |

---

## 23. Scalability Requirements

| Aspect | Current | Growth (12 bulan) |
|---|---|---|
| Posts per day | 3-5 | 3-5 (stable) |
| History items | 180 max | 180 max |
| Storage (video temp) | ~50MB per run (Manim larger output) | ~50MB (temporary, deleted) |
| Storage (history) | ~50KB | ~50KB |

No scalability concerns. Single-threaded sequential execution.

---

## 24. Multi-Tenancy Considerations

N/A — Single Facebook Page, single user.

---

## 25. Data Retention Policy

| Data | Retention | Deletion |
|---|---|---|
| history.json entries | 60 hari (180 entries max) | Auto-purge oldest saat nambah baru |
| Generated video files | Sesi berakhir | Deleted after upload/error |
| Manim cache files | Sesi berakhir | Deleted in cleanup |
| GitHub Actions logs | 90 hari (GitHub policy) | Automatic |

---

## 26. Edge Cases

| ID | Edge Case | Related FR | Handling |
|---|---|---|---|
| EC-001 | Gemini return invalid JSON | FR-001 | Retry 3x, final fail -> skip |
| EC-002 | Token Facebook expired | FR-003 | Telegram notif, jangan simpan history |
| EC-003 | Disk space habis (Manim cache) | FR-002 | Flush cache, cleanup, notif |
| EC-004 | Network failure upload | FR-003 | Retry 1x, fail -> notif |
| EC-005 | Manim render terlalu lama (>8 menit) | FR-002 | Timeout, kill process, cleanup, skip |
| EC-006 | LaTeX tidak terinstall | FR-002 | Fallback ke Text (non-LaTeX) di Manim |
| EC-007 | BGM file missing | FR-009 | Render tanpa audio |
| EC-008 | Font file missing | FR-002 | Fallback ke Manim default |
| EC-009 | Semua topik terpakai hari ini | FR-008 | Reset pool, allow repeat |
| EC-010 | History file corrupt | FR-005 | Backup .corrupt, start fresh |

---

## 27. Risk Assessment

| ID | Risk | Likelihood | Impact | Mitigation | Linked Assumption |
|---|---|---|---|---|---|
| RISK-001 | Manim Community Edition tidak bisa render headless di GitHub Actions | Low | Critical | Test rendering di ubuntu-latest sebelum deploy; alternatif: ManimGL dengan virtual framebuffer | ASM-001 |
| RISK-002 | Manim rendering melebihi 8 menit | Medium | High | Optimasi scene (kurangi animasi complexity, gunakan low_quality preset); timeout + skip | ASM-002 |
| RISK-003 | Memory/CPU tidak cukup di GitHub Actions runner | Medium | High | Scene sederhana (2D text + basic shapes); monitor memory | ASM-003 |
| RISK-004 | Facebook API endpoint berubah | Low | High | Gunakan versioned API (v22.0) | ASM-005 |
| RISK-005 | Manim cache menghabiskan disk space | Medium | Medium | Disable caching, flush setelah render | ASM-008 |
| RISK-006 | LaTeX installation gagal atau terlalu besar | Medium | Medium | apt-get texlive-latex-base (minimal); fallback non-LaTeX | ASM-009 |
| RISK-007 | Facebook token 60-day expiry | Medium | Medium | Pre-emptive check; System User token (long-lived) | |
| RISK-008 | Git conflict history.json (concurrent runs) | Low | Low | Sequential cron, 1 run at a time | |

---

## 28. Acceptance Criteria

| ID | Related FR | Given | When | Then |
|---|---|---|---|---|
| AC-001 | FR-001 | Gemini API key valid | Bot memanggil Gemini | Menerima JSON valid dengan semua field |
| AC-002 | FR-002 | Narasi valid | Bot render video Manim | File MP4 1080x1920, durasi 15-30 detik, ada animasi |
| AC-003 | FR-003 | Video valid + token valid | Bot upload ke Facebook | Response berisi post ID |
| AC-004 | FR-004 | Waktu cron tiba | Workflow trigger | Script main.py tereksekusi |
| AC-005 | FR-005 | Soal sudah ada di history | Bot deteksi duplikat | Tolak soal, generate ulang |
| AC-006 | FR-006 | Error terjadi | Bot kirim Telegram | Admin terima pesan error |
| AC-007 | FR-007 | Semua content type | Bot pilih salah satu | Content type valid dari 3 daftar |
| AC-008 | FR-008 | Topik hari ini sudah dipakai | Bot pilih topik lain | Topik unik untuk hari ini |
| AC-009 | FR-009 | BGM tersedia | Bot composite audio | Video memiliki audio track |
| AC-010 | FR-010 | Video selesai | Inspeksi scene | Ada animasi (bukan static frame) |
| AC-011 | FR-011 | Caption digenerate | Cek hook + CTA | Caption memiliki hook + CTA |
| AC-012 | FR-012 | Sesi selesai | Cek Manim cache | Cache directory kosong |
| AC-013 | FR-013 | Caption dengan engagement bait | Compliance check | Posting BLOCKED, history tidak tersimpan |
| AC-014 | FR-014 | Render selesai | Cek scene 1 | Label content type muncul dengan animasi |

---

## 28a. Traceability Matrix

| BO | FR/NFR | AC | Risk |
|---|---|---|---|
| BO-001 | FR-001, FR-002, FR-003, FR-007, FR-009, FR-010, FR-011, FR-014 | AC-001, AC-002, AC-003, AC-007, AC-009, AC-010, AC-011, AC-014 | RISK-001, RISK-002, RISK-003, RISK-004 |
| BO-002 | FR-004, FR-008 | AC-004, AC-008 | |
| BO-003 | FR-005 | AC-005 | |
| BO-004 | NFR-006 | — | |
| BO-005 | FR-006 | AC-006 | |
| BO-006 | FR-002, FR-012, NFR-003, NFR-004 | AC-002, AC-012 | RISK-002, RISK-005 |
| BO-007 | FR-013, NFR-008 | AC-013 | |
| | NFR-001, NFR-002, NFR-005, NFR-007 | — | |
| | NFR-006 | — | |

---

## 29. Release Strategy

| Phase | Scope | Timeline |
|---|---|---|
| Phase 1 (Prototype) | Test Manim rendering di GitHub Actions: scene sederhana, ukur waktu render, validasi headless capability | Day 1 |
| Phase 2 (MVP) | Single script: generate -> render Manim -> post -> history | Day 1-2 |
| Phase 2a | GitHub Actions workflow + cron + Manim dependency install | Day 2 |
| Phase 3 | 3 content types (quiz/fakta/tips) + animasi berbeda per type | Day 2-3 |
| Phase 4 | Hook + CTA templates, compliance block | Day 3 |
| Phase 5 | Scene optimization: balancing render time vs visual quality | Day 3-4 |
| Phase 6 | Production ramp: 3-5 post/hari + monitoring | Day 4-7 |
| Growth Month | Full operation, daily execution | Day 7-30 |

---

## 30. Future Enhancements

- Scene complexity tiers: simple (fast render) / medium / complex (slow render, high quality)
- Cross-platform posting (Instagram, TikTok)
- Voiceover AI (gTTS)
- Dynamic scene generation based on soal structure (grafik, geometri, dll)
- Variety of animation templates per content type

---

## 31. Technical Recommendations

| Layer | Recommendation | Justification |
|---|---|---|
| Language | Python 3.12 | Sama dengan project sebelumnya, Manim CE support |
| AI | Gemini 3.1 Flash Lite | Gratis, fast, JSON mode support |
| Animation Engine | **Manim Community Edition** (`pip install manim`) | Stable, headless Cairo renderer, active community, dokumentasi lengkap |
| Video Post-Process | FFmpeg (audio mixing) | Standar, sudah tersedia di GitHub Actions via apt |
| BGM | Bundled MP3 (free license) | No streaming dependency |
| Scheduler | GitHub Actions cron | Gratis, built-in secrets |
| Persistence | JSON file | Cukup untuk 180 entries |
| Error Notif | Telegram Bot API | Gratis, real-time |

**Key difference from v1:** Manim CE menggantikan Pillow + MoviePy. Manim menghasilkan video MP4 langsung (tidak perlu frame compositing manual). BGM ditambahkan post-render via FFmpeg.

---

## 32. Effort & Resource Estimation

| Feature Group | Estimated Effort | Roles Required | Critical Path |
|---|---|---|---|
| Manim Prototype (render test on GHA) | 0.5 day | 1 engineer | RISK-001, RISK-002 validation |
| Narasi + Validasi (sama seperti v1) | 0.5 day | 1 engineer | FR-001 |
| Manim Scene Templates (3 content types) | 2 day | 1 engineer | FR-002, FR-010, FR-014 |
| Facebook Upload + Error Handling | 0.5 day | 1 engineer | FR-003, FR-006 |
| Caption Builder + Compliance | 0.5 day | 1 engineer | FR-011, FR-013 |
| Scheduling + History | 0.5 day | 1 engineer | FR-004, FR-008, FR-005 |
| Audio Post-Process (FFmpeg BGM) | 0.25 day | 1 engineer | FR-009 |
| Testing + Debug | 1 day | 1 engineer | All |

**Total: ~5.75 days (single engineer full-time)** — lebih lama dari v1 karena Manim scene templates perlu dirancang untuk 3 content type dengan animasi.

Estimates are indicative based on project complexity, not committed.

---

## 33. Glossary

| Term | Definition |
|---|---|
| Manim CE | Manim Community Edition — fork dari 3b1b/manim, animation engine untuk video matematika |
| Gemini | Google AI model (gemini-3.1-flash-lite) untuk generate teks |
| Reels | Format video pendek portrait di Facebook |
| Scene | Satu segmen animasi dalam Manim (setara frame di MoviePy) |
| Cairo Renderer | Backend rendering Manim yang tidak butuh GPU (CPU-based) |
| LaTeX | Typesetting system untuk rumus matematika (native di Manim) |
| BGM | Background Music |
| FFmpeg | Multimedia framework (audio/video processing) |

---

## 34. Final Validation Summary

| Checklist Item | Status |
|---|---|
| Stakeholders defined | ✓ |
| User roles defined | ✓ |
| Workflows defined (+ alternate + failure) | ✓ |
| Permissions defined | ✓ |
| Validations defined | ✓ |
| Reports defined | ✓ |
| Notifications defined | ✓ |
| Integrations defined | ✓ |
| Audit requirements defined | ✓ |
| Security requirements defined | ✓ |
| Performance targets defined | ✓ |
| Retention policy defined | ✓ |
| Risks documented | ✓ |
| Assumptions documented | ✓ |
| Acceptance criteria defined | ✓ |
| Traceability matrix complete | ✓ |

**Outstanding Gaps:**
- Perlu prototyping Manim rendering di GitHub Actions untuk validasi RISK-001 dan RISK-002
- Scene template Manim untuk 3 content type perlu desain detail di Phase 3 (Architecture)
