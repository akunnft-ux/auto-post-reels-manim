# Implementation Plan — Auto Post Reels Manim

## 1. Overview

Mengimplementasikan bot auto-posting Reels animasi matematika menggunakan Python + Manim CE + Gemini AI.

## 2. Feature Breakdown

| # | Feature | Files | Dependencies | Est. Effort |
|---|---|---|---|---|
| 1 | Manim Scene Templates | `scenes.py` | manim, FFmpeg, LaTeX | 2 day |
| 2 | Narasi Generator (Gemini) | `main.py` | google-genai | 0.5 day |
| 3 | Caption Builder + Compliance | `main.py` | — | 0.5 day |
| 4 | Audio Compositor (FFmpeg) | `main.py` | FFmpeg | 0.25 day |
| 5 | Facebook Poster | `main.py` | requests | 0.5 day |
| 6 | History Manager + Scheduler | `main.py` | json | 0.5 day |
| 7 | GHA Workflow | `.github/workflows/auto-post.yml` | — | 0.5 day |

## 3. File Structure

```
auto-post-reels-manim/
  +- main.py                    # Bot orchestrator
  +- scenes.py                  # Manim scene classes (3 content types)
  +- requirements.txt           # Python deps
  +- .env.example               # Env template
  +- .gitignore                 # Git ignore
  +- data/
  |   +- history.json           # Post history
  |   +- mode.json              # Post mode (telegram/facebook)
  +- fonts/
  |   +- DejaVuSans.ttf         # Font files (copied from existing)
  |   +- DejaVuSans-Bold.ttf
  +- audio/
  |   +- *.mp3                  # BGM files (copied from existing)
  +- docs/
  |   +- discovery-report.md    # Phase 1
  |   +- prd.md                 # Phase 2
  |   +- architecture.md        # Phase 3
  |   +- database.md            # Phase 3
  |   +- implementation-plan.md # Phase 5 (this file)
  +- .github/workflows/
      +- auto-post.yml          # GHA workflow
```

## 4. Dependencies

### Python Packages (requirements.txt)
```
google-genai>=1.0.0
requests>=2.31.0
manim>=0.19.0
Pillow>=10.0.0
moviepy>=2.0.0
```

### System Dependencies (GitHub Actions)
- `ffmpeg` — video processing, audio mixing
- `texlive-latex-base`, `texlive-latex-extra` — LaTeX rendering in Manim
- `libpango1.0-dev` — Manim text rendering on Linux

## 5. Library Docs Verified

- **Manim CE (manimcommunity/manim):** `tempconfig()` for in-process rendering; `pixel_width=1080, pixel_height=1920` for portrait; `quality="low_quality"` for speed; headless Cairo renderer works without display
- **Gemini API:** JSON mode via `responseMimeType: "application/json"` confirmed working
- **Facebook Graph API v22.0:** Multipart video upload to `/{page_id}/videos`

## 6. Risks

| Risk | Mitigation |
|---|---|
| Manim rendering time >8 menit | Low quality preset, scene simplification, timeout |
| Manim crash di GHA runner | In-process rendering with try/except, fallback simplified scene |
| LaTeX install terlalu besar | texlive-latex-base minimal; Text fallback |
| FFmpeg tidak tersedia | apt install in workflow |

## 7. Implementation Order

1. `scenes.py` — Manim scene classes (templates for quiz/fakta/tips)
2. `main.py` — Bot logic (all modules)
3. `requirements.txt` + `.env.example` + `.gitignore`
4. `data/history.json` + `data/mode.json`
5. `.github/workflows/auto-post.yml`
6. Copy fonts/ and audio/ from existing project
