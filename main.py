import glob
import json
import os
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import date, datetime

from google import genai
import requests

HISTORY_FILE = "data/history.json"
MODE_FILE = "data/mode.json"
MAX_HISTORY_ITEMS = 180
MANIM_TIMEOUT = 480

CONTENT_TYPES = ["quiz", "fakta", "tips"]
CONTENT_TYPE_WEIGHTS = {"quiz": 0.4, "fakta": 0.3, "tips": 0.3}

TOPICS = {
    "deret_angka": "Deret Angka",
    "aritmatika_aljabar": "Aritmatika & Aljabar",
    "peluang_statistika": "Peluang & Statistika",
    "geometri": "Geometri",
    "fungsi_grafik": "Fungsi & Grafik",
}

HOOK_TEMPLATES = {
    "quiz": [
        "90% orang salah jawab soal ini. Coba kamu? \U0001F9D0",
        "Kebanyakan orang terkecoh. Pasti kamu bisa! \u26A1",
        "Hanya 1 dari 10 orang yang benar. Ayo coba! \U0001F3AF",
        "Jangan terkecoh dengan soalnya! \U0001F4A1",
        "Menurutmu jawabannya apa? Coba tebak dulu! \U0001F914",
    ],
    "fakta": [
        "Ternyata selama ini kamu salah! Cek videonya \u23EF\uFE0F",
        "Fakta mengejutkan yang jarang orang tahu! \U0001F92F",
        "Mind blowing! Matematika itu tidak seperti yang kamu kira \U0001F92F",
        "Kebanyakan guru juga salah menjelaskan ini! \U0001F631",
        "Baru tahu setelah lulus? Simak ini! \U0001FAE0",
    ],
    "tips": [
        "Hitung dalam 3 detik! Rahasianya di sini \u26A1",
        "Cara ini bikin kamu jago matematika dalam 1 menit! \U0001F525",
        "Trik cepat yang gak diajarin di sekolah! \U0001F4A1",
        "Anti panik! Begini cara cepatnya \u2705",
        "Save video ini! Pasti berguna nanti \U0001F4CC",
    ],
}

CTA_POOL = [
    "Follow untuk soal baru setiap hari! \U0001F525",
    "Follow akun ini biar makin jago matematika! \U0001F4DA",
    "Jangan lupa follow buat latihan tiap hari! \u2705",
    "Follow for more daily soal + tips! \U0001F680",
    "Klik follow biar gak ketinggalan soal baru! \U0001F4DD",
]

HASHTAG_POOL = [
    "#SoalMatematika", "#CPNS2026", "#BelajarMatematika",
    "#MatematikaDasar", "#CPNS", "#TIUCPNS", "#SKDCPNS",
    "#TryoutCPNS", "#RuangBelajar", "#Matematika",
    "#LatihanCPNS", "#StudiCPNS",
]


def _load_json(path, default=None):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []


def _save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def notify_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print(f"[WARN] TELEGRAM not configured. Would send: {message[:200]}")
        return
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message[:4096]}, timeout=10)
    except Exception as e:
        print(f"[WARN] Telegram notification failed: {e}")


def load_history():
    return _load_json(HISTORY_FILE, [])


def save_history(history):
    if len(history) > MAX_HISTORY_ITEMS:
        history = history[-MAX_HISTORY_ITEMS:]
    _save_json(HISTORY_FILE, history)


def get_used_topics_today(history):
    today = date.today().isoformat()
    return {h["topik"] for h in history if h.get("tanggal") == today}


def is_duplicate(soal_text, history):
    return any(h["soal"] == soal_text for h in history)


def pick_topic(history):
    used_today = get_used_topics_today(history)
    available = [t for t in TOPICS if t not in used_today]
    if not available:
        available = list(TOPICS.keys())
    return random.choice(available)


def pick_content_type():
    types = list(CONTENT_TYPE_WEIGHTS.keys())
    weights = [CONTENT_TYPE_WEIGHTS[t] for t in types]
    return random.choices(types, weights=weights, k=1)[0]


def get_hook(content_type):
    return random.choice(HOOK_TEMPLATES[content_type])


def get_cta():
    return random.choice(CTA_POOL)


def generate_narasi(topic, history, content_type, max_retry=3):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    client = genai.Client(api_key=api_key)
    topic_label = TOPICS[topic]
    recent = history[-20:] if history else []

    if content_type == "quiz":
        prompt = f"""Buat 1 soal matematika untuk persiapan CPNS/TKA/SNBT dengan topik {topic_label}.

Soal harus berbentuk pilihan ganda dengan 4 opsi (A, B, C, D). Buat soal yang agak menjebak dan banyak orang salah menjawabnya.

Format output JSON:
{{
  "soal": "teks soal lengkap",
  "pilihan": ["A. ...", "B. ...", "C. ...", "D. ..."],
  "jawaban": "A. ...",
  "penjelasan": "pembahasan singkat mengapa jawaban itu benar dan yang lain salah"
}}

Aturan:
- Soal dalam Bahasa Indonesia
- Tingkat kesulitan sedang-cukup sulit (CPNS/TKA/SNBT)
- Jawaban harus sesuai dengan salah satu pilihan (teks lengkap)
- Jangan buat soal yang sama dengan soal-soal sebelumnya
- Soal sebelumnya: {json.dumps(recent, ensure_ascii=False)}
- Maksimal 2 kalimat PENDek untuk soal, total maksimal 120 karakter
- Penjelasan maksimal 3 kalimat, total maksimal 180 karakter
- Setiap pilihan jawaban maksimal 50 karakter (setelah prefix A/B/C/D)"""
    elif content_type == "fakta":
        prompt = f"""Buat 1 konten fakta matematika yang mengejutkan dan jarang diketahui orang, terkait topik {topic_label}.

Format output JSON:
{{
  "soal": "fakta matematika yang mengejutkan (1-2 kalimat)",
  "pilihan": ["Penjelasan lanjutan 1", "Penjelasan lanjutan 2", "Penjelasan lanjutan 3", "Penjelasan lanjutan 4"],
  "jawaban": "fakta yang benar (sesuai pilihan yang paling tepat)",
  "penjelasan": "penjelasan ilmiah/detail dari fakta tersebut (2-3 kalimat)"
}}

Aturan:
- Fakta harus BENAR secara matematis, jangan menyesatkan
- Bahasa Indonesia
- Maksimal 2 kalimat PENDek untuk fakta, total maksimal 120 karakter
- Penjelasan maksimal 3 kalimat, total maksimal 180 karakter"""
    else:
        prompt = f"""Buat 1 tips/trik cepat matematika untuk persiapan CPNS/TKA/SNBT dengan topik {topic_label}.

Format output JSON:
{{
  "soal": "pertanyaan atau masalah yang sering muncul (1 kalimat)",
  "pilihan": ["A. Cara umum (lambat)", "B. Cara umum lainnya", "C. Cara cepat (trikinya)", "D. Cara salah yang umum"],
  "jawaban": "C. Cara cepat (trikinya)",
  "penjelasan": "penjelasan trik cepat langkah demi langkah (2-3 kalimat)"
}}

Aturan:
- Tips harus BENAR secara matematis
- Bahasa Indonesia
- Soal maksimal 120 karakter (1 kalimat pendek)
- Setiap pilihan maksimal 40 karakter
- Penjelasan maksimal 180 karakter (2-3 kalimat pendek)"""

    for attempt in range(1, max_retry + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            narasi = json.loads(response.text)
            required = {"soal", "pilihan", "jawaban", "penjelasan"}
            if not all(k in narasi for k in required):
                print(f"[WARN] Missing fields, retry {attempt}")
                continue
            if len(narasi["pilihan"]) != 4:
                print(f"[WARN] Not 4 options, retry {attempt}")
                continue
            if narasi["jawaban"] not in narasi["pilihan"]:
                print(f"[WARN] Jawaban not in pilihan, retry {attempt}")
                continue
            if is_duplicate(narasi["soal"], history):
                print(f"[WARN] Duplicate soalan, retry {attempt}")
                continue
            return narasi
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"[WARN] Gemini attempt {attempt} failed: {e}")
            if attempt == max_retry:
                raise
    raise RuntimeError(f"Failed to generate content after {max_retry} attempts")


def render_manim_scene(narasi, topic, content_type, output_path):
    from manim import config, tempconfig
    from scenes import QuizScene, FaktaScene, TipsScene

    scene_map = {"quiz": QuizScene, "fakta": FaktaScene, "tips": TipsScene}
    scene_class = scene_map.get(content_type, QuizScene)

    scene_config = {
        "quality": "low_quality",
        "disable_caching": True,
        "preview": False,
        "pixel_width": 1080,
        "pixel_height": 1920,
        "frame_rate": 24,
        "output_file": output_path,
    }

    with tempconfig(scene_config):
        instance = scene_class()
        instance.data = {
            "soal": narasi["soal"],
            "pilihan": narasi["pilihan"],
            "jawaban": narasi["jawaban"],
            "penjelasan": narasi["penjelasan"],
            "topik": topic,
            "content_type": content_type,
        }
        instance.render()

    rendered_file = instance.renderer.file_writer.movie_file_path
    if os.path.exists(rendered_file):
        if rendered_file != output_path:
            shutil.move(rendered_file, output_path)
        return output_path
    raise RuntimeError(f"Manim render produced no output file")


def composite_bgm(video_path, output_path):
    bgm_files = glob.glob("audio/*.mp3")
    if not bgm_files:
        print("[INFO] No BGM files found, skipping audio")
        return video_path

    bgm_path = random.choice(bgm_files)
    print(f"[INFO] Using BGM: {bgm_path}")

    temp_output = output_path + ".tmp.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", bgm_path,
        "-filter_complex", "[1:a]volume=0.15[a1];[0:a][a1]amix=inputs=2:duration=first",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        "-movflags", "+faststart",
        temp_output,
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        shutil.move(temp_output, output_path)
        return output_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        print(f"[WARN] BGM composite failed: {e}")
        if os.path.exists(temp_output):
            os.remove(temp_output)
        return video_path


def compliance_check(caption):
    disallowed_bait_patterns = [
        "comment.*if you", "comment.*if agree", "tag.*friends",
        "tag 5", "share this.*see", "share.*to win",
    ]
    caption_lower = caption.lower()
    for pattern in disallowed_bait_patterns:
        if re.search(pattern, caption_lower):
            raise ValueError(f"Compliance: engagement bait pattern '{pattern}' detected")
    return True


def build_caption(narasi, topic, content_type, hook):
    topic_label = TOPICS.get(topic, topic)
    cta = get_cta()
    tags = " ".join(random.sample(HASHTAG_POOL, k=min(6, len(HASHTAG_POOL))))

    body = f"{narasi['soal']}\n\n{', '.join(narasi['pilihan'])}"
    caption = f"{hook}\n\n{body}\n\n{cta}\n\n{tags}"
    return caption


def check_fb_token():
    token = os.environ.get("FB_ACCESS_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    if not token or not page_id:
        return False, "FB_ACCESS_TOKEN or FB_PAGE_ID not set"
    try:
        resp = requests.get(
            f"https://graph.facebook.com/v22.0/{page_id}",
            params={"access_token": token, "fields": "id,name"},
            timeout=15,
        )
        if resp.status_code == 200:
            return True, None
        elif resp.status_code == 401:
            return False, "BLOCKED_TOKEN_EXPIRED: Facebook token expired or invalid"
        else:
            return False, f"Token check failed: {resp.status_code} {resp.text}"
    except requests.RequestException as e:
        return False, f"Token check network error: {e}"


def post_to_facebook(video_path, caption):
    token = os.environ.get("FB_ACCESS_TOKEN")
    page_id = os.environ.get("FB_PAGE_ID")
    if not token or not page_id:
        raise ValueError("FB_ACCESS_TOKEN or FB_PAGE_ID not set")

    valid, err = check_fb_token()
    if not valid:
        notify_telegram(f"[BLOCKED] {err}")
        raise PermissionError(err)

    compliance_check(caption)

    url = f"https://graph.facebook.com/v22.0/{page_id}/videos"
    with open(video_path, "rb") as f:
        files = {"source": (os.path.basename(video_path), f, "video/mp4")}
        data = {"description": caption, "access_token": token}
        resp = requests.post(url, files=files, data=data, timeout=120)

    if resp.status_code == 200:
        result = resp.json()
        print(f"[OK] Posted to Facebook Reels. Post ID: {result.get('id')}")
        return result
    elif resp.status_code == 401:
        notify_telegram("[BLOCKED_TOKEN_EXPIRED] Facebook token expired during upload")
        raise PermissionError("Token expired")
    elif resp.status_code == 429:
        notify_telegram(f"[RATE_LIMITED] Facebook rate limited: {resp.text[:200]}")
        raise RuntimeError("Rate limited")
    else:
        body = resp.text[:500]
        notify_telegram(f"[ERROR] Facebook upload failed: {resp.status_code} {body}")
        raise RuntimeError(f"Facebook upload failed: {resp.status_code}")


def post_to_telegram(video_path, caption):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required")
    url = f"https://api.telegram.org/bot{token}/sendVideo"
    with open(video_path, "rb") as f:
        files = {"video": f}
        data = {"chat_id": chat_id, "caption": caption[:1024], "supports_streaming": True}
        resp = requests.post(url, files=files, data=data, timeout=120)
    if not resp.ok:
        raise RuntimeError(f"Telegram sendVideo failed: {resp.status_code} {resp.text[:200]}")
    msg_id = resp.json()["result"]["message_id"]
    print(f"[OK] Sent to Telegram. Message ID: {msg_id}")


def check_telegram_mode():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return "telegram"

    current_mode = "telegram"
    last_id = 0
    if os.path.exists(MODE_FILE):
        with open(MODE_FILE) as f:
            d = json.load(f)
            current_mode = d.get("mode", "telegram")
            last_id = d.get("last_update_id", 0)

    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": last_id + 1, "timeout": 5},
        )
        if resp.ok:
            for upd in resp.json().get("result", []):
                uid = upd["update_id"]
                if uid > last_id:
                    last_id = uid
                    text = (upd.get("message") or {}).get("text", "").strip().lower()
                    if text == "/mode facebook":
                        current_mode = "facebook"
                        requests.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            json={"chat_id": chat_id, "text": "\u2705 Mode berubah ke FACEBOOK"},
                            timeout=10,
                        )
                    elif text == "/mode telegram":
                        current_mode = "telegram"
                        requests.post(
                            f"https://api.telegram.org/bot{token}/sendMessage",
                            json={"chat_id": chat_id, "text": "\u2705 Mode berubah ke TELEGRAM"},
                            timeout=10,
                        )
    except Exception as e:
        print(f"[WARN] Telegram mode check failed: {e}")

    os.makedirs("data", exist_ok=True)
    with open(MODE_FILE, "w") as f:
        json.dump({"mode": current_mode, "last_update_id": last_id}, f)
    return current_mode


def cleanup_manim_cache():
    cache_dirs = [
        os.path.expanduser("~/.ManimCache"),
        os.path.expanduser("~/.cache/manim"),
    ]
    for d in cache_dirs:
        if os.path.exists(d):
            try:
                shutil.rmtree(d, ignore_errors=True)
                print(f"[INFO] Cleaned Manim cache: {d}")
            except Exception as e:
                print(f"[WARN] Could not clean cache {d}: {e}")


def main():
    print(f"[START] Auto Post Reels Manim — {datetime.now().isoformat()}")
    start_time = time.time()
    tmpdir = tempfile.mkdtemp()
    video_path = None
    final_video = None

    try:
        print("[STEP] 1/9 Load history")
        history = load_history()

        print("[STEP] 2/9 Pick content type & topic")
        content_type = pick_content_type()
        topic = pick_topic(history)
        hook = get_hook(content_type)
        print(f"  Content Type: {content_type}, Topic: {topic}")

        print("[STEP] 3/9 Generate content via Gemini")
        narasi = generate_narasi(topic, history, content_type)
        print(f"  Soal: {narasi['soal'][:80]}...")

        print("[STEP] 4/9 Build caption & compliance check")
        caption = build_caption(narasi, topic, content_type, hook)
        compliance_check(caption)
        print(f"  Caption OK ({len(caption)} chars)")

        print("[STEP] 5/9 Render Manim animation scene")
        raw_video = os.path.join(tmpdir, "raw_scene.mp4")
        render_start = time.time()
        render_manim_scene(narasi, topic, content_type, raw_video)
        render_time = time.time() - render_start
        print(f"  Manim render took {render_time:.1f}s")

        print("[STEP] 6/9 Composite BGM")
        bgm_video = os.path.join(tmpdir, "bgm_scene.mp4")
        bgm_result = composite_bgm(raw_video, bgm_video)
        final_video = bgm_result

        print("[STEP] 7/9 Check post mode")
        mode = check_telegram_mode()
        print(f"  Mode: {mode}")

        if mode == "facebook":
            print("[STEP] 8/9 Post to Facebook Reels")
            result = post_to_facebook(final_video, caption)
            post_id = result.get("id", "unknown")
        else:
            print("[STEP] 8/9 Post to Telegram")
            post_to_telegram(final_video, caption)
            post_id = "telegram"

        print("[STEP] 9/9 Save history")
        entry = {
            "soal": narasi["soal"],
            "jawaban": narasi["jawaban"],
            "topik": topic,
            "content_type": content_type,
            "tanggal": date.today().isoformat(),
        }
        history.append(entry)
        save_history(history)
        print(f"  History: {len(history)} entries")

        elapsed = time.time() - start_time
        print(f"\n[DONE] Completed in {elapsed:.1f}s")
        notify_telegram(
            f"[OK] Reels posted successfully!\n"
            f"  Type: {content_type} | Topic: {topic}\n"
            f"  Render: {render_time:.1f}s | Total: {elapsed:.1f}s\n"
            f"  Post ID: {post_id}"
        )

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = f"[ERROR] {datetime.now().isoformat()} - {e}"
        print(f"\n{error_msg}")
        traceback.print_exc()
        notify_telegram(f"[ERROR] {e}\nElapsed: {elapsed:.1f}s")
        sys.exit(1)

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
        if final_video and os.path.exists(final_video) and final_video.startswith(tmpdir):
            os.remove(final_video)
        cleanup_manim_cache()


if __name__ == "__main__":
    main()
