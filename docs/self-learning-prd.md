# PRD: Self-Learning Engine — Auto Post Reels Manim

## Document Control

**Version History**

| Version | Date | Author | Summary of Changes |
|---|---|---|---|
| 0.1 | 2026-06-25 | Tech Lead | Initial draft — self-learning feature addendum |

This document is adapted from `auto-post-reels-matematika/docs/self-learning-prd.md`. All sections (1–14) of that document apply equally to this bot unless noted below.

## Per-Bot Differences

| Aspect | auto-post-reels-matematika (reference) | auto-post-reels-manim |
|---|---|---|
| Existing analytics | ✅ Has analytics.json, growth.json, classify_performance(), run_analytics_batch() | ❌ None — must build from scratch |
| Content types | quiz, fakta, tips | quiz, fakta, tips ✅ (same) |
| Learning scope | weights + hooks + CTA + hashtags | weights + hooks + CTA + hashtags ✅ (same) |
| HOOK_TEMPLATES | Existing (5 per content type) | **Does not exist** — must add hook pool |
| CTA_POOL | Existing (5 items) | Existing (5 items) ✅ |
| HASHTAG_POOL | Existing (12 items) | Existing (12 items) ✅ |
| main.py style | 1130 lines, argparse CLI | 636 lines, no argparse |
| GA workflow | `data/*.json` glob — auto-catches new files | Explicit `data/history.json data/mode.json` — **must update** |
| Telegram handling | Has `download_telegram_file()` + `parse_csv_with_gemini()` | No CSV handling — must build |
| Concurrency group | ❌ Not set | ✅ Already has `concurrency: group: auto-post` |

## Impact on GA Workflow

The file `auto-post-reels-manim/.github/workflows/auto-post.yml` must be updated:

1. Change `git add data/history.json data/mode.json` → `git add data/*.json`
2. Add stash-rebase pattern (like the other 2 bots) to prevent push conflicts
3. Add `if: always()` guard to commit step

## All Other Sections

Refer to `auto-post-reels-matematika/docs/self-learning-prd.md` Sections 1–14 for:
- Business Objectives (BO-001 through BO-003)
- Functional Requirements (FR-SL-001 through FR-SL-010)
- Non-Functional Requirements (NFR-SL-001 through NFR-SL-004)
- Data Requirements (analytics_record, classification_record, learning_iteration, learning_config schemas)
- Business Rules (BR-SL-001 through BR-SL-006)
- Workflow diagrams
- Acceptance Criteria (AC-SL-001 through AC-SL-010)
- Traceability Matrix
- Risk Assessment
- Release Strategy
- Effort Estimate
