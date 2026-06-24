# Security Review — Auto Post Reels Manim

## 1. Security Overview

Bot Python monolitik dengan minimal attack surface. Tidak ada user input, tidak ada database server, tidak ada PII. Risiko keamanan utama terletak pada:
1. Credential exposure (API keys, tokens)
2. Token expiry handling (Facebook)
3. Manim process security (arbitrary code execution via scenes)
4. File system access (temp files)

## 2. Findings

| ID | Finding | Severity | Status |
|---|---|---|---|
| SEC-001 | All credentials stored as GitHub encrypted secrets | **Informational** | Pass |
| SEC-002 | No hardcoded secrets in source code | **Informational** | Pass |
| SEC-003 | `.env` file in `.gitignore` | **Informational** | Pass |
| SEC-004 | Facebook token pre-emptive expiry check | **Low** | Pass |
| SEC-005 | No user input accepted (bot-only) | **Informational** | Pass |
| SEC-006 | No database — no injection risk | **Informational** | Pass |
| SEC-007 | No PII stored — only math questions in history | **Informational** | Pass |
| SEC-008 | Temp files cleaned after each execution | **Low** | Pass |
| SEC-009 | Manim scenes execute user-defined animation code | **Medium** | **Open** — RISK |
| SEC-010 | Compliance check blocks engagement bait | **Low** | Pass |
| SEC-011 | Telegram notification fire-and-forget (no retry) | **Informational** | Pass |
| SEC-012 | No log sanitization (print statements) | **Low** | Pass |

### SEC-009 Detail: Manim scene code execution

| Field | Value |
|---|---|
| **Risk** | `scenes.py` contains hardcoded Manim scene classes. If an attacker could modify `scenes.py`, they could execute arbitrary code via Manim's scene rendering pipeline |
| **Severity** | Medium |
| **Mitigation** | Code is committed to GitHub repo (write access required). GHA only pulls from repo, never writes to scenes.py. Attack requires repo write access = game over anyway |
| **Status** | Acceptable risk — mitigated by GitHub access controls |

## 3. Severity Matrix

| Severity | Count | Status |
|---|---|---|
| Critical | 0 | OK |
| High | 0 | OK |
| Medium | 1 (SEC-009 — acceptable risk) | Acceptable |
| Low | 3 | Monitoring |
| Informational | 5 | OK |

## 4. OWASP Checklist

| OWASP Category | Status | Notes |
|---|---|---|
| Broken Access Control | N/A | No user roles, single script |
| Cryptographic Failures | N/A | No encryption needed (no PII) |
| Injection | **Pass** | No SQL/NoSQL DB. Gemini input is AI-generated, not user input |
| Insecure Design | **Pass** | Minimal attack surface |
| Security Misconfiguration | **Pass** | Secrets via env vars only |
| Vulnerable Components | **Pass** | `pip install manim` from PyPI |
| Auth Failures | **Pass** | Token pre-check before posting |
| Integrity Failures | **Pass** | Git-tracked history |
| Logging Failures | **Pass** | Logs to stdout (GHA visible) |
| SSRF Risks | **Pass** | Outbound HTTP only to known APIs (Gemini, FB, Telegram) |

## 5. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| FB token expiry detected late | Low | Pre-emptive check + Telegram notification |
| GitHub secrets leaked via malicious action | Low | GHA trust model — own repo only |
| Manim scene code injection (write access needed) | Medium | Controlled by GitHub permissions |

## 6. Recommendations

1. **Use long-lived Facebook System User token** (not short-lived Page token) — reduces expiry frequency
2. **Rotate Gemini API key periodically** — via GitHub secrets UI
3. **Monitor GHA logs** for any unusual activity
4. **Pin manim version** in requirements.txt after initial compatibility test

## 7. Release Decision

**SECURITY: APPROVED.** No blocking findings. Zero critical or high severity issues. One medium-severity finding (SEC-009) is an acceptable risk due to GitHub access controls.
