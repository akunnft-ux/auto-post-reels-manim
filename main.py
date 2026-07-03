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
from PIL import Image, ImageDraw, ImageFont
import requests

HISTORY_FILE = "data/history.json"
MODE_FILE = "data/mode.json"
PRODUCT_ROTATION_FILE = "data/product_rotation.json"
PRODUCT_LINKS_FILE = "data/product_links.json"
PRODUCT_ASSETS_DIR = "assets/shopee"
MAX_HISTORY_ITEMS = 180
MANIM_TIMEOUT = 600  # Increased from 480 for LaTeX compile overhead
LEARNING_CONFIG_FILE = "self_learning/learning_config.json"

HOOK_SECONDS = 2
PRODUCT_SLIDE_SECONDS = 2
IMG_WIDTH = 1080
IMG_HEIGHT = 1920

CONTENT_TYPES = ["quiz", "fakta", "tips"]
CONTENT_TYPE_WEIGHTS = {"quiz": 0.4, "fakta": 0.3, "tips": 0.3}

TOPICS = {
    "deret_angka": "Deret Angka",
    "aritmatika_aljabar": "Aritmatika & Aljabar",
    "peluang_statistika": "Peluang & Statistika",
    "geometri": "Geometri",
    "fungsi_grafik": "Fungsi & Grafik",
}

FONT_BOLD = "fonts/DejaVuSans-Bold.ttf"
FONT_REGULAR = "fonts/DejaVuSans.ttf"

BG_COLOR = "#FFF8E7"
HEADER_BG = "#1B2A4A"
HEADER_TEXT = "#FFFFFF"
TOPIC_BG = {"deret_angka": "#FF6B9D", "aritmatika_aljabar": "#FF8C42", "peluang_statistika": "#A8E6CF", "geometri": "#7EC8E3", "fungsi_grafik": "#DDA0DD"}
TOPIC_TEXT = "#FFFFFF"
SOAL_TEXT = "#2C3E50"
PILIHAN_BG = "#FFFFFF"
PILIHAN_ACCENT = "#FF8C42"
PILIHAN_TEXT = "#2C3E50"
JAWABAN_BG = "#FFE0EC"
JAWABAN_ACCENT = "#FF6B9D"
JAWABAN_TEXT = "#8B2252"
PENJELASAN_TEXT = "#475569"
FOOTER_TEXT = "#94A3B8"

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


def load_product_rotation():
    rotation = _load_json(PRODUCT_ROTATION_FILE, {"current_index": 0})
    if "current_index" not in rotation:
        rotation["current_index"] = 0
    return rotation


def save_product_rotation(index):
    _save_json(PRODUCT_ROTATION_FILE, {"current_index": index})


def pick_product():
    rotation = load_product_rotation()
    idx = rotation["current_index"]

    product_dirs = sorted([
        d for d in os.listdir(PRODUCT_ASSETS_DIR)
        if os.path.isdir(os.path.join(PRODUCT_ASSETS_DIR, d))
    ]) if os.path.isdir(PRODUCT_ASSETS_DIR) else []

    if not product_dirs:
        print("[WARN] No product directories found in assets/shopee/")
        return None

    if idx >= len(product_dirs):
        idx = 0

    product_name = product_dirs[idx]
    product_path = os.path.join(PRODUCT_ASSETS_DIR, product_name)
    images = sorted([
        os.path.join(product_path, f)
        for f in os.listdir(product_path)
        if f.lower().endswith((".webp", ".png", ".jpg", ".jpeg"))
    ])

    if len(images) < 3:
        print(f"[WARN] Product '{product_name}' has only {len(images)} images (need 3)")
        return None

    print(f"[INFO] Selected product: {product_name} (index {idx})")
    return {"index": idx, "name": product_name, "images": images[:3], "next_index": (idx + 1) % max(len(product_dirs), 1)}


def load_product_links():
    if not os.path.exists(PRODUCT_LINKS_FILE):
        print(f"[WARN] Product links file not found: {PRODUCT_LINKS_FILE}")
        return {}
    with open(PRODUCT_LINKS_FILE, "r") as f:
        links = json.load(f)
    return {entry["id_produk"]: entry for entry in links}


def get_link_for_product(product):
    links = load_product_links()
    if product is None:
        return None
    name = product.get("name")
    if not name or name not in links:
        print(f"[WARN] No link found for product: {name}")
        return None
    entry = links[name]
    return entry.get("link_komisi_ekstra", entry["link_produk"])


SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
    'n': 'ⁿ', 'a': 'ᵃ', 'b': 'ᵇ', 'm': 'ᵐ',
    'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ', 'f': 'ᶠ', 'g': 'ᵍ',
    'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ', 'k': 'ᵏ', 'l': 'ˡ',
    'o': 'ᵒ', 'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ',
    'u': 'ᵘ', 'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ',
    'z': 'ᶻ',
}

FRACTION_MAP = {
    '1/2': '½', '1/3': '⅓', '2/3': '⅔',
    '1/4': '¼', '3/4': '¾',
    '1/5': '⅕', '2/5': '⅖', '3/5': '⅗', '4/5': '⅘',
    '1/6': '⅙', '5/6': '⅚',
    '1/7': '⅐',
    '1/8': '⅛', '3/8': '⅜', '5/8': '⅝', '7/8': '⅞',
    '1/9': '⅑',
    '1/10': '⅒',
}

SUBSCRIPT_MAP = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
    'a': 'ₐ', 'e': 'ₑ', 'o': 'ₒ', 'x': 'ₓ',
    'h': 'ₕ', 'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ',
    'n': 'ₙ', 'p': 'ₚ', 's': 'ₛ', 't': 'ₜ',
}

def fix_math_notation(text: str) -> str:
    text = re.sub(
        r'\^\{([^}]*)\}',
        lambda m: ''.join(SUPERSCRIPT_MAP.get(c, c) for c in m.group(1)),
        text,
    )
    text = re.sub(
        r'\^\(([^)]+)\)',
        lambda m: ''.join(SUPERSCRIPT_MAP.get(c, c) for c in m.group(1)),
        text,
    )
    text = re.sub(
        r'\^(\d+)',
        lambda m: ''.join(SUPERSCRIPT_MAP.get(c, c) for c in m.group(1)),
        text,
    )
    text = re.sub(
        r'\^([a-z])',
        lambda m: SUPERSCRIPT_MAP.get(m.group(1), m.group(1)),
        text,
    )
    text = re.sub(r'\bsqrt\b', '√', text)
    text = re.sub(r'\bpi\b', 'π', text)
    text = text.replace('>=', '≥').replace('<=', '≤').replace('!=', '≠')

    def _replace_frac(m):
        frac = m.group(0)
        if frac in FRACTION_MAP:
            return FRACTION_MAP[frac]
        num, den = frac.split('/')
        sup = ''.join(SUPERSCRIPT_MAP.get(c, c) for c in num)
        sub = ''.join(SUBSCRIPT_MAP.get(c, c) for c in den)
        return sup + '⁄' + sub
    text = re.sub(r'(?<!\d)(\d+)/(\d+)(?!\d)', _replace_frac, text)
    return text


def _verify_answer_factually(soal, pilihan, jawaban, client, content_type):
    """Verify answer correctness via independent Gemini re-evaluation (quiz only)."""
    if content_type != "quiz":
        return True

    jawaban_letter = re.match(r'^([A-D])', jawaban)
    if not jawaban_letter:
        return True

    prompt = f"""Selesaikan soal matematika berikut secara mandiri. JANGAN terpengaruh jawaban siapapun.

SOAL: {soal}
PILIHAN:
{chr(10).join(pilihan)}

Kerjakan langkah demi langkah, lalu berikan jawaban dalam format JSON:
{{"jawaban_benar": "huruf (A, B, C, atau D)"}}"""

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config={"response_mime_type": "application/json"},
        )
        result = json.loads(response.text)
        verified = result.get("jawaban_benar", "").strip().upper()
        if verified in ("A", "B", "C", "D"):
            match = verified == jawaban_letter.group(1)
            if not match:
                print(f"  [VERIFY] Independent answer={verified} vs original={jawaban_letter.group(1)} — MISMATCH")
            return match
        return True
    except Exception as e:
        print(f"  [VERIFY] Error: {e}")
        return True


def _sanitize_latex(latex_str):
    """Fix common double-escaping from Gemini JSON output."""
    return latex_str.replace("\\\\", "\\")


def _validate_latex(latex_str):
    """Validate LaTeX string by attempting MathTex compile."""
    from manim import MathTex
    try:
        MathTex(latex_str)
        return True
    except Exception as e:
        print(f"  [LATEX] Invalid: '{latex_str[:60]}...' error: {e}")
        return False


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
  "penjelasan": "pembahasan singkat mengapa jawaban itu benar dan yang lain salah",
  "soal_latex": "\\\\text{{Tentukan nilai x dari }} \\\\sqrt{{x+1}} = 3",
  "jawaban_latex": "x = 8",
  "pilihan_latex": ["A. 5", "B. 6", "C. 7", "D. 8"],
  "penjelasan_latex": "\\\\text{{Diketahui }} \\\\sqrt{{x+1}} = 3 \\\\text{{, kuadratkan: }} x+1 = 9 \\\\text{{, maka }} x = 8"
}}

Aturan:
- Soal dalam Bahasa Indonesia
- Tingkat kesulitan sedang-cukup sulit (CPNS/TKA/SNBT)
- Jawaban harus sesuai dengan salah satu pilihan (teks lengkap)
- Jangan buat soal yang sama dengan soal-soal sebelumnya
- Soal sebelumnya: {json.dumps(recent, ensure_ascii=False)}
- Maksimal 2 kalimat PENDek untuk soal, total maksimal 120 karakter
- Penjelasan maksimal 3 kalimat, total maksimal 180 karakter
- Setiap pilihan jawaban maksimal 50 karakter (setelah prefix A/B/C/D)
- Gunakan Unicode untuk notasi matematika: x² bukan x^2, √4 bukan sqrt(4), π bukan pi, × bukan x, ≤ bukan <=, ≠ bukan !=, ≥ bukan >=
- TAMBAHKAN field soal_latex, jawaban_latex, pilihan_latex, penjelasan_latex
- soal_latex: LaTeX dari teks soal, termasuk perintah soal menggunakan \\text{{}}. Contoh: "\\\\text{{Tentukan nilai x dari }} \\\\sqrt{{x+1}} = 3"
- jawaban_latex: string LaTeX murni (hanya persamaan, tanpa prefix huruf)
- pilihan_latex: list 4 item LaTeX, pertahankan prefix "A. " dll. Contoh: "A. \\\\sqrt{{2}}"
- penjelasan_latex: LaTeX dari pembahasan, gunakan \\text{{}} untuk teks naratif. Contoh: "\\\\text{{Diketahui }} \\\\sqrt{{x+1}} = 3 \\\\text{{, maka }} x = 8"
- Hanya gunakan \\sqrt{{}}, \\sqrt[n]{{}}, \\frac{{}}{{}}, ^, _ — standar amsmath
- Backslash di JSON: tulis \\\\ untuk setiap backslash
- Gunakan huruf x sebagai variabel utama yang perlu disorot nanti di video"""
    elif content_type == "fakta":
        prompt = f"""Buat 1 konten fakta matematika yang mengejutkan dan jarang diketahui orang, terkait topik {topic_label}.

Format output JSON:
{{
  "soal": "fakta matematika yang mengejutkan (1-2 kalimat)",
  "pilihan": ["Penjelasan lanjutan 1", "Penjelasan lanjutan 2", "Penjelasan lanjutan 3", "Penjelasan lanjutan 4"],
  "jawaban": "fakta yang benar (sesuai pilihan yang paling tepat)",
  "penjelasan": "penjelasan ilmiah/detail dari fakta tersebut (2-3 kalimat)",
  "soal_latex": "\\\\sqrt{{2}} \\\\approx 1.414",
  "jawaban_latex": "\\\\sqrt{{2}} \\\\approx 1.414",
  "penjelasan_latex": "\\\\text{{Nilai }} \\\\sqrt{{2}} \\\\text{{ adalah sekitar 1.414}}"
}}

Aturan:
- Fakta harus BENAR secara matematis, jangan menyesatkan
- Bahasa Indonesia
- Maksimal 2 kalimat PENDek untuk fakta, total maksimal 120 karakter
- Penjelasan maksimal 3 kalimat, total maksimal 180 karakter
- Gunakan Unicode untuk notasi matematika: x² bukan x^2, π bukan pi
- TAMBAHKAN soal_latex, jawaban_latex, dan penjelasan_latex (string LaTeX murni, gunakan \\text{{}} untuk teks naratif)
- Backslash di JSON: tulis \\\\ untuk setiap backslash. Contoh LaTeX \\sqrt{{2}} ditulis sebagai "\\\\sqrt{{2}}" dalam JSON"""
    else:
        prompt = f"""Buat 1 tips/trik cepat matematika untuk persiapan CPNS/TKA/SNBT dengan topik {topic_label}.

Format output JSON:
{{
  "soal": "pertanyaan atau masalah yang sering muncul (1 kalimat)",
  "pilihan": ["A. Cara umum (lambat)", "B. Cara umum lainnya", "C. Cara cepat (trikinya)", "D. Cara salah yang umum"],
  "jawaban": "C. Cara cepat (trikinya)",
  "penjelasan": "penjelasan trik cepat langkah demi langkah (2-3 kalimat)",
  "soal_latex": "\\\\sqrt{{144}} + \\\\sqrt{{25}}",
  "jawaban_latex": "\\\\text{{Cara cepat}}",
  "penjelasan_latex": "\\\\text{{Pertama hitung }} \\\\sqrt{{144}} = 12"
}}

Aturan:
- Tips harus BENAR secara matematis
- Bahasa Indonesia
- Soal maksimal 120 karakter (1 kalimat pendek)
- Setiap pilihan maksimal 40 karakter
- Penjelasan maksimal 180 karakter (2-3 kalimat pendek)
- Gunakan Unicode untuk notasi matematika: x² bukan x^2, √ bukan sqrt, π bukan pi
- TAMBAHKAN soal_latex, jawaban_latex, dan penjelasan_latex (string LaTeX murni)
- soal_latex: LaTeX dari teks soal
- jawaban_latex: LaTeX dari jawaban (cukup teks triknya, tanpa prefix C.)
- penjelasan_latex: LaTeX dari penjelasan, gunakan \\text{{}} untuk teks naratif
- Backslash di JSON: tulis \\\\ untuk setiap backslash. Contoh LaTeX \\sqrt{{144}} ditulis sebagai "\\\\sqrt{{144}}" dalam JSON"""

    for attempt in range(1, max_retry + 1):
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            narasi = json.loads(response.text)
            required = {"soal", "pilihan", "jawaban", "penjelasan", "soal_latex", "jawaban_latex", "penjelasan_latex"}
            if not all(k in narasi for k in required):
                print(f"[WARN] Missing fields, retry {attempt}")
                continue
            if len(narasi["pilihan"]) != 4:
                print(f"[WARN] Not 4 options, retry {attempt}")
                continue
            if narasi["jawaban"] not in narasi["pilihan"]:
                print(f"[WARN] Jawaban not in pilihan, retry {attempt}")
                continue

            jawaban_letter = re.match(r'^([A-D])', narasi["jawaban"])
            if jawaban_letter:
                penjelasan_letter = re.search(
                    r'(?:jawaban|kunci|benar)\s*(?:adalah|:|\s)*\s*([A-D])\b',
                    narasi["penjelasan"],
                )
                if penjelasan_letter and jawaban_letter.group(1) != penjelasan_letter.group(1):
                    print(
                        f"[WARN] Label mismatch: jawaban='{jawaban_letter.group(1)}' "
                        f"vs penjelasan='{penjelasan_letter.group(1)}', retry {attempt}"
                    )
                    continue

            # VALIDASI 1: Fakta verification — independent Gemini re-evaluation
            if not _verify_answer_factually(narasi["soal"], narasi["pilihan"], narasi["jawaban"], client, content_type):
                print(f"[WARN] Fakta answer mismatch, retry {attempt}")
                continue

            narasi["soal"] = fix_math_notation(narasi["soal"])
            narasi["pilihan"] = [fix_math_notation(p) for p in narasi["pilihan"]]
            narasi["jawaban"] = fix_math_notation(narasi["jawaban"])
            narasi["penjelasan"] = fix_math_notation(narasi["penjelasan"])

            if narasi["jawaban"] not in narasi["pilihan"]:
                print(f"[WARN] Jawaban not in pilihan after formatting, retry {attempt}")
                continue

            if is_duplicate(narasi["soal"], history):
                print(f"[WARN] Duplicate soalan, retry {attempt}")
                continue

            # Sanitize and validate LaTeX fields
            narasi["soal_latex"] = _sanitize_latex(narasi["soal_latex"])
            narasi["jawaban_latex"] = _sanitize_latex(narasi["jawaban_latex"])
            narasi["penjelasan_latex"] = _sanitize_latex(narasi["penjelasan_latex"])
            latex_ok = _validate_latex(narasi["soal_latex"])
            latex_ok = _validate_latex(narasi["jawaban_latex"]) and latex_ok
            latex_ok = _validate_latex(narasi["penjelasan_latex"]) and latex_ok
            if content_type == "quiz":
                if "pilihan_latex" not in narasi or len(narasi["pilihan_latex"]) != 4:
                    print(f"[WARN] Missing pilihan_latex, retry {attempt}")
                    continue
                narasi["pilihan_latex"] = [_sanitize_latex(p) for p in narasi["pilihan_latex"]]
                for pl in narasi["pilihan_latex"]:
                    latex_ok = _validate_latex(pl) and latex_ok
            if not latex_ok:
                print(f"[WARN] LaTeX validation failed, retry {attempt}")
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
            "soal_latex": narasi.get("soal_latex", narasi["soal"]),
            "jawaban_latex": narasi.get("jawaban_latex", narasi["jawaban"]),
            "pilihan_latex": narasi.get("pilihan_latex", narasi["pilihan"]),
            "penjelasan_latex": narasi.get("penjelasan_latex", narasi["penjelasan"]),
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

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", video_path],
        capture_output=True, text=True, timeout=10,
    )
    has_audio = bool(probe.stdout.strip())

    temp_output = output_path + ".tmp.mp4"
    if has_audio:
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
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", bgm_path,
            "-filter_complex", "[1:a]volume=0.15[a1]",
            "-map", "0:v:0",
            "-map", "[a1]",
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


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def wrap_text(text, font, draw, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_rounded_rect(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def render_frame_hook(hook_text, topic, output_path):
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), hex_to_rgb(HEADER_BG))
    draw = ImageDraw.Draw(img)

    font_big = ImageFont.truetype(FONT_BOLD, 72)
    font_sub = ImageFont.truetype(FONT_REGULAR, 32)
    font_badge = ImageFont.truetype(FONT_BOLD, 28)

    accent = TOPIC_BG.get(topic, "#FF8C42")
    accent_rgb = hex_to_rgb(accent)

    overlay = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), (*accent_rgb, 30))
    img.paste(overlay, (0, 0), overlay)

    topic_label = TOPICS.get(topic, topic)
    bbox = draw.textbbox((0, 0), f"\u2728 {topic_label}", font=font_badge)
    badge_w = bbox[2] - bbox[0] + 30
    badge_h = bbox[3] - bbox[1] + 14
    badge_y = 60
    badge_x = (IMG_WIDTH - badge_w) // 2
    draw_rounded_rect(draw, [badge_x, badge_y, badge_x + badge_w, badge_y + badge_h], 20, accent_rgb)
    draw.text((badge_x + 15, badge_y + 7), f"\u2728 {topic_label}", fill="#FFFFFF", font=font_badge)

    hook_lines = wrap_text(hook_text, font_big, draw, IMG_WIDTH - 120)
    total_h = len(hook_lines) * 90
    start_y = (IMG_HEIGHT - total_h) // 2
    for line in hook_lines:
        draw.text((IMG_WIDTH // 2, start_y), line, fill="#FFFFFF", font=font_big, anchor="mt")
        start_y += 90

    draw.text((IMG_WIDTH // 2, IMG_HEIGHT - 80), "Geser untuk jawaban \u25BC", fill="#94A3B8", font=font_sub, anchor="mt")

    img.save(output_path)
    return output_path


def render_product_slides(product, tmpdir):
    from moviepy import ImageClip

    slides = []
    for i, img_path in enumerate(product["images"]):
        try:
            frame_path = os.path.join(tmpdir, f"product_{i}.png")
            img = Image.open(img_path).convert("RGBA")
            img_w, img_h = img.size
            scale = IMG_WIDTH / img_w
            new_h = int(img_h * scale)
            img = img.resize((IMG_WIDTH, new_h), Image.LANCZOS)

            canvas = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), (0, 0, 0))
            y_offset = (IMG_HEIGHT - new_h) // 2
            canvas.paste(img, (0, y_offset), img if img.mode == "RGBA" else None)
            canvas.save(frame_path)

            slide = ImageClip(frame_path, duration=PRODUCT_SLIDE_SECONDS)
            slides.append(slide)
        except Exception as e:
            print(f"[WARN] Failed to load product image {img_path}: {e}")
            continue
    return slides


def composite_hook_and_products(manim_video, output_path, hook_text, topic, product):
    from moviepy import ImageClip, VideoFileClip, concatenate_videoclips

    tmpdir = tempfile.mkdtemp()
    try:
        clips = []

        if hook_text:
            try:
                hook_frame = os.path.join(tmpdir, "hook.png")
                render_frame_hook(hook_text, topic, hook_frame)
                hook_clip = ImageClip(hook_frame, duration=HOOK_SECONDS)
                clips.append(hook_clip)
                print(f"[INFO] Hook frame rendered ({HOOK_SECONDS}s)")
            except Exception as e:
                print(f"[WARN] Hook render failed, skipping: {e}")

        main_clip = VideoFileClip(manim_video)
        clips.append(main_clip)

        if product is not None:
            try:
                product_slides = render_product_slides(product, tmpdir)
                if product_slides:
                    clips.extend(product_slides)
                    print(f"[INFO] Added {len(product_slides)} product slides from {product['name']}")
            except Exception as e:
                print(f"[WARN] Product slide render failed, skipping: {e}")

        if len(clips) == 1:
            shutil.copy2(manim_video, output_path)
            return output_path

        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
        final.close()
        return output_path
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


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


def load_and_apply_learning_config():
    if not os.path.exists(LEARNING_CONFIG_FILE):
        return
    try:
        with open(LEARNING_CONFIG_FILE) as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"[WARN] Failed to load learning config: {e}")
        return

    global CONTENT_TYPE_WEIGHTS, HOOK_TEMPLATES, CTA_POOL, HASHTAG_POOL
    changed = []
    if "content_type_weights" in cfg and cfg["content_type_weights"]:
        CONTENT_TYPE_WEIGHTS = cfg["content_type_weights"]
        changed.append("weights")
    if "hook_templates" in cfg and cfg["hook_templates"]:
        HOOK_TEMPLATES = cfg["hook_templates"]
        changed.append("hooks")
    if "cta_pool" in cfg and cfg["cta_pool"]:
        CTA_POOL = cfg["cta_pool"]
        changed.append("CTA")
    if "hashtag_pool" in cfg and cfg["hashtag_pool"]:
        HASHTAG_POOL = cfg["hashtag_pool"]
        changed.append("hashtags")
    if changed:
        print(f"[SL] Applied learning config: {', '.join(changed)}")


def process_telegram_csv():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return

    last_id = 0
    if os.path.exists(MODE_FILE):
        with open(MODE_FILE) as f:
            last_id = json.load(f).get("last_update_id", 0)

    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": last_id + 1, "timeout": 5},
        )
        if not resp.ok:
            return

        for upd in resp.json().get("result", []):
            uid = upd["update_id"]
            if uid <= last_id:
                continue
            msg = upd.get("message") or {}
            doc = msg.get("document")
            if doc and doc.get("file_name", "").lower().endswith(".csv"):
                print(f"[SL] CSV detected: {doc['file_name']}")
                tmp_path = f"/tmp/sl_csv_{doc['file_id']}.csv"
                if _download_telegram_file(doc["file_id"], tmp_path, token):
                    try:
                        from self_learning import run_self_learning
                        result = run_self_learning(tmp_path)
                        notify_telegram(_format_sl_summary(result))
                    except Exception as e:
                        notify_telegram(f"[SL] Self-learning FAILED: {e}")
                        print(f"[SL] Error: {e}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)
    except Exception as e:
        print(f"[WARN] process_telegram_csv failed: {e}")


def _download_telegram_file(file_id, dest_path, token):
    resp = requests.get(
        f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}", timeout=15
    )
    if not resp.ok:
        return False
    file_path = resp.json()["result"]["file_path"]
    dl = requests.get(
        f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=30
    )
    if not dl.ok:
        return False
    with open(dest_path, "wb") as f:
        f.write(dl.content)
    print(f"[SL] CSV downloaded ({len(dl.content)} bytes)")
    return True


def _format_sl_summary(result: dict) -> str:
    if result.get("status") == "skipped":
        return f"[SL] Self-learning skipped: {result.get('reason', 'unknown')}"
    lines = ["[SL] Self-learning selesai!"]
    lines.append(f"Records diproses: {result.get('records_parsed', 0)}")
    cls = result.get("classifications", {})
    if cls:
        lines.append(f"Viral: {cls.get('viral', 0)} | Good: {cls.get('good', 0)} | Bad: {cls.get('bad', 0)}")
    changes = result.get("changes_made", [])
    if changes:
        lines.append(f"Perubahan: {', '.join(changes)}")
    return "\n".join(lines)


def main():
    print(f"[START] Auto Post Reels Manim — {datetime.now().isoformat()}")
    start_time = time.time()
    tmpdir = tempfile.mkdtemp()
    video_path = None
    final_video = None

    try:
        load_and_apply_learning_config()
        process_telegram_csv()

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

        print("[STEP] 4b/9 Pre-render answer verification")
        verify_client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        if not _verify_answer_factually(narasi["soal"], narasi["pilihan"], narasi["jawaban"], verify_client, content_type):
            print("[WARN] Second verification failed. Regenerating content...")
            narasi = generate_narasi(topic, history, content_type, max_retry=5)
            caption = build_caption(narasi, topic, content_type, hook)
            compliance_check(caption)

        print("[STEP] 5/9 Pick product rotation")
        product = pick_product()
        if product:
            print(f"  Product: {product['name']} (index {product['index']})")
        else:
            print("  No product available")

        product_link_msg = get_link_for_product(product)
        if product_link_msg:
            print(f"  Product link: {product_link_msg[:60]}...")
        else:
            print("  No product link available")

        print("[STEP] 6/9 Render Manim animation scene")
        raw_video = os.path.join(tmpdir, "raw_scene.mp4")
        render_start = time.time()
        render_manim_scene(narasi, topic, content_type, raw_video)
        render_time = time.time() - render_start
        print(f"  Manim render took {render_time:.1f}s")

        print("[STEP] 7/9 Composite hook + products + manim")
        wrapped_video = os.path.join(tmpdir, "wrapped_scene.mp4")
        composite_hook_and_products(raw_video, wrapped_video, hook, topic, product)

        print("[STEP] 8/9 Composite BGM")
        bgm_video = os.path.join(tmpdir, "bgm_scene.mp4")
        bgm_result = composite_bgm(wrapped_video, bgm_video)
        final_video = bgm_result

        print("[STEP] 9/9 Check post mode")
        mode = check_telegram_mode()
        print(f"  Mode: {mode}")

        if mode == "facebook":
            print("[STEP] 10/9 Post to Facebook Reels")
            result = post_to_facebook(final_video, caption)
            post_id = result.get("id", "unknown")
        else:
            print("[STEP] 10/9 Post to Telegram")
            if product_link_msg:
                caption = caption + f"\n\n🔗 {product_link_msg}"
            post_to_telegram(final_video, caption)
            post_id = "telegram"

        print("[STEP] 11/9 Save history")
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

        if product is not None:
            save_product_rotation(product["next_index"])
            print(f"  Product rotation saved: index {product['next_index']}")

        elapsed = time.time() - start_time
        print(f"\n[DONE] Completed in {elapsed:.1f}s")

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
