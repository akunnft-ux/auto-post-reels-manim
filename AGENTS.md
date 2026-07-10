# Agent Memory — auto-post-reels-manim

## Fixes Applied (2026-07-10)

### Fix #2: CSV Parser `_extract_record()`
- `csv_parser.py`: `_extract_record()` membaca `account_type`, `format`, `theme` dari CSV column mapping, bukan hardcoded None

### Fix #5: Redundant `_verify_answer_factually()`
- `main.py`: Hapus redundant `_verify_answer_factually()` call kedua di step 4b — sudah dipanggil sekali di step 3, hasilnya disimpan di `answer_data`

### Fix #6: Import json
- `csv_parser.py`: Pindahkan `import json` ke atas file

### Fix #7: STAGGER_MIN_HOURS
- `main.py`: Tambah `STAGGER_MIN_HOURS = 3` konsisten
- Pastikan `load_and_apply_learning_config()` return `cfg`
