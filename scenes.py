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
    "geometri": "#4DABF7",
    "fungsi_grafik": "#9775FA",
}


def get_topic_color(topic: str) -> str:
    return TOPIC_COLORS.get(topic, "#868E96")


def create_topic_badge(topic: str, scene: Scene) -> VGroup:
    color = get_topic_color(topic)
    badge = Rectangle(width=2.0, height=0.5, color=color, fill_opacity=0.2)
    label = Text(topic.replace("_", " ").title(), font_size=16, color=color)
    group = VGroup(badge, label)
    label.move_to(badge.get_center())
    return group


class QuizScene(Scene):
    def construct(self):
        data = self.data
        soal = data["soal"]
        pilihan = data["pilihan"]
        jawaban = data["jawaban"]
        penjelasan = data["penjelasan"]
        topic = data["topik"]
        colors = CONTENT_COLORS["quiz"]

        # Phase 1: Soal (5-8 seconds)
        title_text = Text("QUIZ CHALLENGE", font_size=36, color=colors["main"])
        subtitle = Text("Coba tebak!", font_size=20, color=colors["accent"])
        title_group = VGroup(title_text, subtitle).arrange(DOWN, buff=0.15)
        title_group.to_edge(UP, buff=0.8)
        self.play(Write(title_text), run_time=1.0)
        self.play(FadeIn(subtitle, shift=UP * 0.2), run_time=0.5)

        topic_badge = create_topic_badge(topic, self)
        topic_badge.next_to(title_group, DOWN, buff=0.3)
        self.play(FadeIn(topic_badge, scale=0.8), run_time=0.5)

        soal_parsed = soal
        if len(soal_parsed) > 120:
            soal_parsed = soal_parsed[:117] + "..."
        soal_text = Text(soal_parsed, font_size=26, color="#2D3436")
        soal_text.scale_to_fit_width(config.frame_width - 1.0)
        soal_text.next_to(topic_badge, DOWN, buff=0.5)
        self.play(Write(soal_text), run_time=1.5)
        self.wait(3.0)
        self.play(FadeOut(VGroup(title_group, topic_badge, soal_text)), run_time=0.5)

        # Phase 2: Pilihan (5-8 seconds)
        header2 = Text("PILIHAN JAWABAN", font_size=32, color=colors["main"])
        header2.to_edge(UP, buff=0.8)
        self.play(Write(header2), run_time=0.8)

        option_labels = ["A", "B", "C", "D"]
        option_group = VGroup()
        for i, opt in enumerate(pilihan):
            opt_clean = opt
            if opt_clean.startswith(f"{option_labels[i]}."):
                opt_clean = opt_clean[2:].strip()
            elif opt_clean.startswith(option_labels[i]):
                opt_clean = opt_clean[1:].strip()
            label = Text(f"{option_labels[i]}.", font_size=22, color=colors["accent"], weight=BOLD)
            text = Text(opt_clean, font_size=20, color="#2D3436")
            text.scale_to_fit_width(config.frame_width - 1.8)
            row = VGroup(label, text).arrange(RIGHT, buff=0.15, aligned_edge=UP)
            card = Rectangle(
                width=config.frame_width - 0.8,
                height=text.height + 0.4,
                color=colors["accent"],
                fill_opacity=0.08,
            )
            card.stroke_width = 1.5
            row.move_to(card.get_center())
            group = VGroup(card, label, text)
            option_group.add(group)

        option_group.arrange(DOWN, buff=0.25, aligned_center=True)
        option_group.move_to(ORIGIN)

        for i, group in enumerate(option_group):
            self.play(FadeIn(group, shift=RIGHT * 0.5), run_time=0.4)

        self.wait(2.0)
        self.play(FadeOut(VGroup(header2, option_group)), run_time=0.5)

        # Phase 3: Pembahasan (5-10 seconds)
        header3 = Text("JAWABAN & PEMBAHASAN", font_size=32, color=colors["main"])
        header3.to_edge(UP, buff=0.8)
        self.play(Write(header3), run_time=0.8)

        jawaban_clean = jawaban
        for label in ["A.", "B.", "C.", "D.", "A", "B", "C", "D"]:
            if jawaban_clean.startswith(label):
                prefix = label.rstrip(".")
                jawaban_clean = jawaban_clean[len(label):].strip()
                break

        jawaban_card = Rectangle(
            width=config.frame_width - 0.8,
            height=0.8,
            color=colors["accent"],
            fill_opacity=0.15,
        )
        jawaban_label = Text("Jawaban:", font_size=22, color=colors["main"], weight=BOLD)
        jawaban_value = Text(jawaban_clean, font_size=24, color=colors["accent"])
        jawaban_content = VGroup(jawaban_label, jawaban_value).arrange(RIGHT, buff=0.3)
        jawaban_content.move_to(jawaban_card.get_center())
        jawaban_group = VGroup(jawaban_card, jawaban_content)

        jawaban_group.next_to(header3, DOWN, buff=0.5)
        self.play(Create(jawaban_card), Write(jawaban_content), run_time=1.0)

        penjelasan_parsed = penjelasan
        if len(penjelasan_parsed) > 200:
            penjelasan_parsed = penjelasan_parsed[:197] + "..."
        penjelasan_text = Text(penjelasan_parsed, font_size=20, color="#636E72")
        penjelasan_text.scale_to_fit_width(config.frame_width - 0.8)
        penjelasan_text.next_to(jawaban_group, DOWN, buff=0.5)
        self.play(Write(penjelasan_text), run_time=1.5)

        self.wait(3.0)
        self.play(FadeOut(VGroup(header3, jawaban_group, penjelasan_text)), run_time=0.5)


class FaktaScene(Scene):
    def construct(self):
        data = self.data
        soal = data["soal"]
        penjelasan = data["penjelasan"]
        topic = data["topik"]
        colors = CONTENT_COLORS["fakta"]

        # Phase 1: Intro
        title_text = Text("FAKTA MATEMATIKA", font_size=36, color=colors["main"])
        subtitle = Text("Mind blowing!", font_size=20, color=colors["accent"])
        title_group = VGroup(title_text, subtitle).arrange(DOWN, buff=0.15)
        title_group.to_edge(UP, buff=0.8)
        self.play(Write(title_text), run_time=1.0)
        self.play(FadeIn(subtitle, shift=UP * 0.2), run_time=0.5)

        topic_badge = create_topic_badge(topic, self)
        topic_badge.next_to(title_group, DOWN, buff=0.3)
        self.play(FadeIn(topic_badge, scale=0.8), run_time=0.5)

        # Phase 2: Fakta statement
        fakta_parsed = soal
        if len(fakta_parsed) > 200:
            fakta_parsed = fakta_parsed[:197] + "..."
        fakta_text = Text(fakta_parsed, font_size=28, color="#2D3436", weight=BOLD)
        fakta_text.scale_to_fit_width(config.frame_width - 0.8)
        fakta_text.next_to(topic_badge, DOWN, buff=0.6)
        self.play(Write(fakta_text), run_time=1.5)
        self.wait(3.0)

        # Phase 3: Explanation
        self.play(
            FadeOut(VGroup(title_group, topic_badge)),
            fakta_text.animate.shift(UP * 2).scale(0.85),
            run_time=1.0,
        )

        penjelasan_parsed = penjelasan
        if len(penjelasan_parsed) > 250:
            penjelasan_parsed = penjelasan_parsed[:247] + "..."
        penjelasan_text = Text(penjelasan_parsed, font_size=22, color="#636E72")
        penjelasan_text.scale_to_fit_width(config.frame_width - 0.8)
        penjelasan_text.next_to(fakta_text, DOWN, buff=0.5)
        self.play(Write(penjelasan_text), run_time=1.5)
        self.wait(3.0)
        self.play(FadeOut(VGroup(fakta_text, penjelasan_text)), run_time=0.5)


class TipsScene(Scene):
    def construct(self):
        data = self.data
        soal = data["soal"]
        penjelasan = data["penjelasan"]
        topic = data["topik"]
        colors = CONTENT_COLORS["tips"]

        # Phase 1: Intro
        title_text = Text("TIPS CEPAT", font_size=36, color=colors["main"])
        subtitle = Text("Catat baik-baik!", font_size=20, color=colors["accent"])
        title_group = VGroup(title_text, subtitle).arrange(DOWN, buff=0.15)
        title_group.to_edge(UP, buff=0.8)
        self.play(Write(title_text), run_time=1.0)
        self.play(FadeIn(subtitle, shift=UP * 0.2), run_time=0.5)

        topic_badge = create_topic_badge(topic, self)
        topic_badge.next_to(title_group, DOWN, buff=0.3)
        self.play(FadeIn(topic_badge, scale=0.8), run_time=0.5)

        # Phase 2: Tip
        tip_parsed = soal
        if len(tip_parsed) > 200:
            tip_parsed = tip_parsed[:197] + "..."
        tip_text = Text(tip_parsed, font_size=28, color="#2D3436", weight=BOLD)
        tip_text.scale_to_fit_width(config.frame_width - 0.8)
        tip_text.next_to(topic_badge, DOWN, buff=0.6)
        self.play(Write(tip_text), run_time=1.5)
        self.wait(3.0)

        # Phase 3: Explanation
        self.play(
            FadeOut(VGroup(title_group, topic_badge)),
            tip_text.animate.shift(UP * 2).scale(0.85),
            run_time=1.0,
        )

        penjelasan_parsed = penjelasan
        if len(penjelasan_parsed) > 250:
            penjelasan_parsed = penjelasan_parsed[:247] + "..."
        penjelasan_text = Text(penjelasan_parsed, font_size=22, color="#636E72")
        penjelasan_text.scale_to_fit_width(config.frame_width - 0.8)
        penjelasan_text.next_to(tip_text, DOWN, buff=0.5)
        self.play(Write(penjelasan_text), run_time=1.5)
        self.wait(3.0)
        self.play(FadeOut(VGroup(tip_text, penjelasan_text)), run_time=0.5)
