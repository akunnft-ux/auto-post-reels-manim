import re
from manim import *

# Portrait 9:16 configuration
config.frame_height = 8
config.frame_width = 4.5
config.pixel_height = 1920
config.pixel_width = 1080

CONTENT_COLORS = {
    "quiz": {"main": "#1B3A5C", "accent": "#FF6B6B", "bg": "#FFF8E7"},
    "fakta": {"main": "#2D5016", "accent": "#FFA94D", "bg": "#F0FFF0"},
    "tips": {"main": "#4A1B5C", "accent": "#4ECDC4", "bg": "#F8F0FF"},
}

TOPIC_COLORS = {
    "deret_angka": "#FF6B9D",
    "aritmatika_aljabar": "#FFA94D",
    "peluang_statistika": "#51CF66",
    "fungsi_grafik": "#9775FA",
}

CHARS_PER_UNIT = {
    28: 14, 24: 16, 22: 18, 20: 20, 26: 15, 32: 12, 36: 10,
    34: 11, 38: 9, 40: 8, 18: 22, 16: 26,
}


def get_topic_color(topic: str) -> str:
    return TOPIC_COLORS.get(topic, "#868E96")


def _split_text_blocks(latex_str, max_chars=18):
    parts = re.split(r'(\\text\{[^}]*\})', latex_str)
    result = []
    for p in parts:
        m = re.match(r'^\\text\{([^}]*)\}$', p)
        if m:
            content = m.group(1)
            if len(content) > max_chars:
                words = content.split()
                lines = []
                cur = []
                for w in words:
                    test = ' '.join(cur + [w])
                    if len(test) > max_chars and cur:
                        lines.append(' '.join(cur))
                        cur = [w]
                    else:
                        cur.append(w)
                if cur:
                    lines.append(' '.join(cur))
                result.extend(f'\\text{{{l} }}' for l in lines)
            else:
                result.append(p)
        else:
            result.append(p)
    return ''.join(result)


def render_equation(latex_str, max_width, font_size=40, color="#2D3436", highlight_color=None, highlight_substrings=None):
    eq = MathTex(latex_str, font_size=font_size, color=color)
    if highlight_color and highlight_substrings:
        eq.set_color_by_tex_to_color_map({s: highlight_color for s in highlight_substrings})
    if eq.width > max_width:
        eq.scale_to_fit_width(max_width)
    return eq


def render_wrapped_latex(latex_str, max_width, font_size=26, color="#2D3436",
                          highlight_color=None, highlight_substrings=None, line_buff=0.08):
    single = MathTex(latex_str, font_size=font_size, color=color)
    if single.width <= max_width:
        if highlight_color and highlight_substrings:
            single.set_color_by_tex_to_color_map({s: highlight_color for s in highlight_substrings})
        return single

    parts = [p for p in re.split(r'(\\text\{[^}]*\})', latex_str) if p]
    lines = []
    current = ""
    for part in parts:
        test = current + part
        test_me = MathTex(test, font_size=font_size)
        if test_me.width > max_width and current:
            lines.append(current)
            current = part
        else:
            current = test
    if current:
        lines.append(current)

    mobs = []
    for line in lines:
        eq = MathTex(line, font_size=font_size, color=color)
        if highlight_color and highlight_substrings:
            eq.set_color_by_tex_to_color_map({s: highlight_color for s in highlight_substrings})
        if eq.width > max_width:
            eq.scale_to_fit_width(max_width)
        mobs.append(eq)

    return VGroup(*mobs).arrange(DOWN, buff=line_buff, aligned_edge=LEFT)


def wrap_text(
    text: str,
    font_size: int,
    max_width: float,
    color="#2D3436",
    weight=NORMAL,
    buff=0.1,
    align=LEFT,
) -> VGroup:
    chars_per_line = CHARS_PER_UNIT.get(font_size, int(max_width * 5))
    words = text.split()
    lines = []
    current = []
    for word in words:
        test = " ".join(current + [word]) if current else word
        if len(test) > chars_per_line and current:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    texts = [Text(l, font_size=font_size, color=color, weight=weight) for l in lines]
    for t in texts:
        if t.width > max_width:
            t.scale_to_fit_width(max_width)
    group = VGroup(*texts).arrange(DOWN, buff=buff, aligned_edge=align)
    return group


def create_topic_badge(topic: str, scene: Scene) -> VGroup:
    color = get_topic_color(topic)
    label = Text(topic.replace("_", " ").title(), font_size=16, color=color)
    padding_x = 0.3
    padding_y = 0.12
    badge = Rectangle(
        width=label.width + padding_x * 2,
        height=label.height + padding_y * 2,
        color=color,
        fill_opacity=0.2,
    )
    label.move_to(badge.get_center())
    return VGroup(badge, label)


class QuizScene(Scene):
    def construct(self):
        data = self.data
        soal = data["soal"]
        pilihan = data["pilihan"]
        jawaban = data["jawaban"]
        penjelasan = data["penjelasan"]
        topic = data["topik"]
        colors = CONTENT_COLORS["quiz"]
        self.camera.background_color = colors["bg"]

        soal_latex = data.get("soal_latex", soal)
        jawaban_latex = data.get("jawaban_latex", jawaban)
        pilihan_latex = data.get("pilihan_latex", pilihan)
        penjelasan_latex = data.get("penjelasan_latex", penjelasan)

        # Phase 1: Soal (5-8 seconds)
        title_text = Text("QUIZ", font_size=32, color=colors["main"])
        title_sub = Text("CHALLENGE", font_size=28, color=colors["accent"])
        title_group = VGroup(title_text, title_sub).arrange(DOWN, buff=0.05)
        title_group.to_edge(UP, buff=0.6)
        self.play(Write(title_text), run_time=0.8)
        self.play(Write(title_sub), run_time=0.5)

        topic_badge = create_topic_badge(topic, self)
        topic_badge.next_to(title_group, DOWN, buff=0.3)
        self.play(FadeIn(topic_badge, scale=0.8), run_time=0.5)

        processed_soal = _split_text_blocks(soal_latex, max_chars=14)
        soal_eq = render_wrapped_latex(
            processed_soal,
            max_width=config.frame_width - 0.6,
            font_size=36,
            color=colors["main"],
            highlight_color=colors["accent"],
            highlight_substrings=["x"],
        )
        soal_eq.next_to(topic_badge, DOWN, buff=0.4)
        self.play(Write(soal_eq), run_time=1.5)
        self.wait(5.0)
        self.play(FadeOut(VGroup(title_group, topic_badge, soal_eq)), run_time=0.5)

        # Phase 2: Pilihan (5-8 seconds)
        header2 = Text("PILIHAN", font_size=32, color=colors["main"])
        header2.to_edge(UP, buff=0.6)
        self.play(Write(header2), run_time=0.8)

        option_labels = ["A", "B", "C", "D"]
        option_group = VGroup()
        for i, opt in enumerate(pilihan):
            opt_latex = pilihan_latex[i] if i < len(pilihan_latex) else opt
            opt_clean = opt
            if opt_clean.startswith(f"{option_labels[i]}."):
                opt_clean = opt_clean[2:].strip()
            elif opt_clean.startswith(option_labels[i]):
                opt_clean = opt_clean[1:].strip()
            opt_latex_clean = opt_latex
            if opt_latex_clean.startswith(f"{option_labels[i]}."):
                opt_latex_clean = opt_latex_clean[2:].strip()
            elif opt_latex_clean.startswith(option_labels[i]):
                opt_latex_clean = opt_latex_clean[1:].strip()
            opt_rendered = render_equation(
                opt_latex_clean,
                max_width=config.frame_width - 2.0,
                font_size=32,
                color=colors["main"],
            )
            label = Text(f"{option_labels[i]}.", font_size=28, color=colors["accent"], weight=BOLD)
            card_h = max(opt_rendered.height + 0.3, 0.5)
            card = Rectangle(
                width=config.frame_width - 0.6,
                height=card_h,
                color=colors["accent"],
                fill_opacity=0.08,
            )
            card.stroke_width = 1.5
            content = VGroup(label, opt_rendered).arrange(RIGHT, buff=0.15, aligned_edge=UP)
            content.move_to(card.get_center(), aligned_edge=LEFT)
            content.shift(LEFT * (card.width / 2 - 0.3))
            group = VGroup(card, content)
            option_group.add(group)

        option_group.arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        option_group.move_to(ORIGIN)

        for g in option_group:
            self.play(FadeIn(g, shift=RIGHT * 0.5), run_time=0.4)

        self.wait(4.0)
        self.play(FadeOut(VGroup(header2, option_group)), run_time=0.5)

        # Phase 3: Pembahasan (5-10 seconds)
        header3 = Text("PEMBAHASAN", font_size=32, color=colors["main"])
        header3.to_edge(UP, buff=0.6)
        self.play(Write(header3), run_time=0.8)

        jawaban_label_prefix = ""
        for label in ["A.", "B.", "C.", "D.", "A", "B", "C", "D"]:
            if jawaban.startswith(label):
                jawaban_label_prefix = label.rstrip(".")
                break

        jawaban_card = Rectangle(
            width=config.frame_width - 0.6,
            height=1.2,
            color=colors["accent"],
            fill_opacity=0.15,
        )
        if jawaban_label_prefix:
            label_part = Text(f"{jawaban_label_prefix}.", font_size=28, color=colors["accent"], weight=BOLD)
            text_part = render_equation(
                jawaban_latex,
                max_width=config.frame_width - 1.5,
                font_size=32,
                color=colors["main"],
                highlight_color=colors["accent"],
                highlight_substrings=["x"],
            )
            jawaban_content = VGroup(label_part, text_part).arrange(RIGHT, buff=0.1)
        else:
            jawaban_content = Text(f"Jawaban: {jawaban_clean}", font_size=18, color=colors["main"])
        jawaban_content.move_to(jawaban_card.get_center())
        jawaban_group = VGroup(jawaban_card, jawaban_content)

        jawaban_group.next_to(header3, DOWN, buff=0.4)
        self.play(Create(jawaban_card), Write(jawaban_content), run_time=1.0)

        penjelasan_group = render_wrapped_latex(
            penjelasan_latex,
            max_width=config.frame_width - 0.6,
            font_size=28,
            color="#636E72",
            highlight_color=colors["accent"],
            highlight_substrings=["x"],
        )
        penjelasan_group.next_to(jawaban_group, DOWN, buff=0.4)
        self.play(Write(penjelasan_group), run_time=1.5)

        self.wait(5.0)
        self.play(FadeOut(VGroup(header3, jawaban_group, penjelasan_group)), run_time=0.5)


class FaktaScene(Scene):
    def construct(self):
        data = self.data
        soal = data["soal"]
        penjelasan = data["penjelasan"]
        topic = data["topik"]
        colors = CONTENT_COLORS["fakta"]
        self.camera.background_color = colors["bg"]

        soal_latex = data.get("soal_latex", soal)

        # Phase 1: Intro
        title_text = Text("FAKTA", font_size=32, color=colors["main"])
        title_sub = Text("Mind blowing!", font_size=24, color=colors["accent"])
        title_group = VGroup(title_text, title_sub).arrange(DOWN, buff=0.05)
        title_group.to_edge(UP, buff=0.6)
        self.play(Write(title_text), run_time=0.8)
        self.play(Write(title_sub), run_time=0.5)

        topic_badge = create_topic_badge(topic, self)
        topic_badge.next_to(title_group, DOWN, buff=0.3)
        self.play(FadeIn(topic_badge, scale=0.8), run_time=0.5)

        # Phase 2: Fakta statement
        fakta_group = render_wrapped_latex(
            soal_latex,
            max_width=config.frame_width - 0.6,
            font_size=36,
            color=colors["main"],
            highlight_color=colors["accent"],
            highlight_substrings=["x"],
        )
        fakta_group.next_to(topic_badge, DOWN, buff=0.5)
        self.play(Write(fakta_group), run_time=1.5)
        self.wait(5.0)

        # Phase 3: Explanation
        self.play(
            FadeOut(VGroup(title_group, topic_badge)),
            fakta_group.animate.shift(UP * 2).scale(0.85),
            run_time=1.0,
        )

        penjelasan_group = wrap_text(penjelasan, 24, config.frame_width - 0.6, color="#636E72", buff=0.08)
        penjelasan_group.next_to(fakta_group, DOWN, buff=0.4)
        self.play(Write(penjelasan_group), run_time=1.5)
        self.wait(5.0)
        self.play(FadeOut(VGroup(fakta_group, penjelasan_group)), run_time=0.5)


class TipsScene(Scene):
    def construct(self):
        data = self.data
        soal = data["soal"]
        penjelasan = data["penjelasan"]
        topic = data["topik"]
        colors = CONTENT_COLORS["tips"]
        self.camera.background_color = colors["bg"]

        soal_latex = data.get("soal_latex", soal)

        # Phase 1: Intro
        title_text = Text("TIPS", font_size=32, color=colors["main"])
        title_sub = Text("Catat baik-baik!", font_size=24, color=colors["accent"])
        title_group = VGroup(title_text, title_sub).arrange(DOWN, buff=0.05)
        title_group.to_edge(UP, buff=0.6)
        self.play(Write(title_text), run_time=0.8)
        self.play(Write(title_sub), run_time=0.5)

        topic_badge = create_topic_badge(topic, self)
        topic_badge.next_to(title_group, DOWN, buff=0.3)
        self.play(FadeIn(topic_badge, scale=0.8), run_time=0.5)

        # Phase 2: Tip
        tip_group = render_wrapped_latex(
            soal_latex,
            max_width=config.frame_width - 0.6,
            font_size=36,
            color=colors["main"],
            highlight_color=colors["accent"],
            highlight_substrings=["x"],
        )
        tip_group.next_to(topic_badge, DOWN, buff=0.5)
        self.play(Write(tip_group), run_time=1.5)
        self.wait(5.0)

        # Phase 3: Explanation
        self.play(
            FadeOut(VGroup(title_group, topic_badge)),
            tip_group.animate.shift(UP * 2).scale(0.85),
            run_time=1.0,
        )

        penjelasan_group = wrap_text(penjelasan, 24, config.frame_width - 0.6, color="#636E72", buff=0.08)
        penjelasan_group.next_to(tip_group, DOWN, buff=0.4)
        self.play(Write(penjelasan_group), run_time=1.5)
        self.wait(5.0)
        self.play(FadeOut(VGroup(tip_group, penjelasan_group)), run_time=0.5)
