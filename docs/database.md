# Database Design — Auto Post Reels Manim

## 1. Database Overview

Bot ini tidak menggunakan database server. Persistence menggunakan JSON file (`data/history.json`) yang di-track oleh git. Pendekatan ini dipilih karena:

- Data sangat kecil (max 180 records)
- Single writer (tidak ada concurrency)
- Git-tracked untuk history dan rollback
- Sama dengan project sebelumnya (proven pattern)

## 2. Entity List

| Entity | File | Purpose | Records |
|---|---|---|---|
| history_entry | data/history.json | Post history untuk anti-duplikasi | Max 180 |

## 3. Entity Definitions

### history_entry

| Field | Type | Required | Description | Example |
|---|---|---|---|---|
| soal | String | Yes | Teks soal matematika | "Jika x^2 - 5x + 6 = 0, nilai x adalah..." |
| jawaban | String | Yes | Jawaban benar (teks lengkap) | "2 atau 3" |
| topik | String | Yes | Topic ID | "deret_angka" |
| content_type | String | Yes | Tipe konten | "quiz" |
| tanggal | String | Yes | Tanggal post (YYYY-MM-DD) | "2026-06-24" |

### Enum: topik

| Value | Description |
|---|---|
| deret_angka | Deret angka dan pola bilangan |
| aritmatika_aljabar | Aritmatika dan aljabar dasar |
| peluang_statistika | Peluang dan statistika |
| geometri | Geometri dan bangun ruang |
| fungsi_grafik | Fungsi dan grafik |

### Enum: content_type

| Value | Description | Weight |
|---|---|---|
| quiz | Quiz challenge soal pilihan ganda | 40% |
| fakta | Fakta matematika menarik | 30% |
| tips | Tips cepat hitung matematika | 30% |

## 4. Relationship Map

```
history_entry (self-contained, no relationships)
```

## 5. ERD (Text)

```
[data/history.json]
  |
  +-- history_entry[]
        +-- soal: string (unique)
        +-- jawaban: string
        +-- topik: string (enum)
        +-- content_type: string (enum)
        +-- tanggal: string (YYYY-MM-DD)
```

## 6. Constraints

| Constraint | Rule |
|---|---|
| Max records | 180 entries |
| Uniqueness | soal field tidak boleh duplikat (exact string match) |
| Topik validity | topik harus dari enum 5 topik |
| Content type validity | content_type harus dari enum 3 type |
| Date format | YYYY-MM-DD |

## 7. Index Strategy

Linear scan. Array <200 items, tidak perlu index.

## 8. Unique Constraints

- `soal` — exact string match untuk anti-duplikasi

## 9. Audit Strategy

| Action | Method |
|---|---|
| Setiap post | Append entry ke history.json |
| History mutation | Git commit (full history tersimpan di git) |
| Error events | GitHub Actions logs (90 hari retention) |

## 10. Reporting Strategy

Tidak ada reporting database. Report di-generate dari:
- history.json (post history)
- GitHub Actions logs (execution history, render time)

## 11. Migration Strategy

| Scenario | Action |
|---|---|
| Add new field | Baca existing entries (mungkin tanpa field baru), default value di code |
| Format change | Tulis ulang file dengan format baru |
| File corruption | Backup .corrupt, start fresh |

## 12. Backup Strategy

| Aspek | Detail |
|---|---|
| Automatic | Git history (setiap commit menyimpan state history.json) |
| Manual | git clone / git pull sudah termasuk backup |
| Recovery | git checkout previous commit untuk rollback |

## 13. Retention Strategy

| Data | Retention | Deletion |
|---|---|---|
| history.json entries | 60 hari (180 entries max) | Auto-purge oldest saat nambah baru |
| Git history | Forever | N/A |

## 14. Security Design

| Concern | Implementation |
|---|---|
| Data exposure | Hanya teks soal publik — tidak ada PII |
| File integrity | Git-tracked, perubahan ter-record |
| Access | Read/write via Python script, only from GitHub Actions runner |

## 15. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| JSON file corruption | Low | Medium | Backup .corrupt, start fresh |
| Git conflict (concurrent runs) | Low | Low | Sequential cron, sequential execution |
| Accidental data deletion | Low | Low | Git recovery |

## 16. Recommendations

1. **Tetap gunakan JSON file** — proven pattern dari project sebelumnya
2. **Max 180 entries** — cukup untuk 60 hari di 3 post/hari
3. **Error handling** — backup file corrupt sebelum reset
4. **Future migration** — jika perlu analytics atau multi-platform data, baru migrasi ke SQLite atau Supabase
