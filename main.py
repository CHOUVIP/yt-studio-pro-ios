# -*- coding: utf-8 -*-
"""
YT Studio Pro — iOS (Kivy)
Port of the desktop YT Studio Pro (PySide6) to iOS. Same cores (ytb_core /
studio_core, v2.3.5 logic incl. Google->Gemini translation rescue), mobile UI.
v3 UI: dark professional theme (CHOUVIP blue), rounded cards, pill tabs,
slide transitions. Copyright: Nguyễn Đình Hà.
"""
import os, sys, json, re, threading, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivy.metrics import dp, sp
from kivy.properties import NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget

import ytb_core as core
import studio_core as sc
from ytb_core import LANGUAGES, LANG_BY_CODE

APP_TITLE = "YT Studio Pro"
OWNER = "Nguyễn Đình Hà"
MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.8-pro"]

# ---------------- theme ----------------
C_BG = (0.043, 0.051, 0.078, 1)        # #0B0D14
C_CARD = (0.086, 0.102, 0.145, 1)      # #161A25
C_FIELD = (0.110, 0.133, 0.188, 1)     # #1C2230
C_FIELD_D = (0.145, 0.176, 0.243, 1)   # pressed field
C_BORDER = (0.165, 0.192, 0.263, 1)    # #2A3143
C_ACCENT = (0.180, 0.486, 0.965, 1)    # #2E7CF6 CHOUVIP blue
C_ACCENT_D = (0.122, 0.396, 0.827, 1)  # #1F65D3
C_GOLD = (0.961, 0.722, 0.239, 1)      # #F5B83D
C_TEXT = (0.929, 0.945, 0.969, 1)      # #EDF1F7
C_SUB = (0.596, 0.635, 0.702, 1)       # #98A2B3
C_MUTED = (0.420, 0.463, 0.525, 1)     # #6B7686
C_DANGER = (0.957, 0.247, 0.369, 1)    # #F43F5E
C_DANGER_D = (0.855, 0.180, 0.310, 1)

_EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF\u2190-\u21FF\u2300-\u23FF\u2600-\u27BF\u2B00-\u2BFF\uFE0F\u200D\u20E3]")


def clean_text(s):
    """Strip emoji (Kivy's Roboto has no emoji glyphs -> tofu boxes on iOS).
    The -> arrow is missing from Roboto too, so swap it for a safe ›."""
    return _EMOJI_RE.sub("", str(s).replace("→", "›")).strip()


# ---- rounded field backgrounds, generated once (pure-stdlib PNG) ----
def _write_png(path, size, rows):
    import struct, zlib

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    raw = b"".join(b"\x00" + r for r in rows)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
    with open(path, "wb") as fh:
        fh.write(png)


def _make_field_png(path, fill, border):
    size, radius, bw = 56, 15, 2.5
    half = (size - 1) / 2.0
    rows = []
    for y in range(size):
        row = bytearray()
        for x in range(size):
            qx = abs(x - half) - (half - radius)
            qy = abs(y - half) - (half - radius)
            sdf = (max(qx, 0) ** 2 + max(qy, 0) ** 2) ** 0.5 + min(max(qx, qy), 0) - radius
            alpha = max(0.0, min(1.0, 0.5 - sdf))
            col = border if sdf > -bw else fill
            row += bytes((int(col[0] * 255), int(col[1] * 255), int(col[2] * 255),
                          int(alpha * 255)))
        rows.append(bytes(row))
    _write_png(path, size, rows)


_BG_CACHE = {}


def field_bg_paths():
    if "n" in _BG_CACHE:
        return _BG_CACHE["n"], _BG_CACHE["f"]
    try:
        base = App.get_running_app().user_data_dir
    except Exception:
        base = os.path.expanduser("~")
    n = os.path.join(base, "field_bg.png")
    f = os.path.join(base, "field_bg_focus.png")
    try:
        if not (os.path.exists(n) and os.path.exists(f)):
            _make_field_png(n, C_FIELD, C_BORDER)
            _make_field_png(f, C_FIELD, C_ACCENT)
    except Exception:
        n, f = "", ""
    _BG_CACHE["n"], _BG_CACHE["f"] = n, f
    return n, f


def open_url(url):
    try:
        from kivy.utils import platform
        if platform == "ios":
            from pyobjus import autoclass
            NSURL = autoclass("NSURL")
            UIApplication = autoclass("UIApplication")
            UIApplication.sharedApplication().openURL_(NSURL.URLWithString_(url))
            return
    except Exception:
        pass
    import webbrowser
    webbrowser.open(url)


def paint_bg(w, color):
    with w.canvas.before:
        Color(*color)
        rect = Rectangle(pos=w.pos, size=w.size)

    def upd(*_):
        rect.pos = w.pos
        rect.size = w.size
    w.bind(pos=upd, size=upd)
    return w


# ---------------- widgets ----------------
class TButton(Button):
    """Rounded button. Variants: primary (blue), danger (red), ghost (field)."""

    def __init__(self, text="", variant="ghost", **kw):
        self.variant = variant
        self.radius_dp = getattr(self, "radius_dp", dp(12))
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height", dp(50))
        super().__init__(text=text, **kw)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = C_TEXT
        self.font_size = sp(15)
        self.bold = variant in ("primary", "danger")
        if "halign" not in kw:
            self.halign = "center"
        if "valign" not in kw:
            self.valign = "middle"
        with self.canvas.before:
            self._bgc = Color(*self._fill())
            self._bgr = RoundedRectangle(pos=self.pos, size=self.size,
                                         radius=[self.radius_dp])
            self._bdc = Color(*C_BORDER)
            self._bdl = Line(rounded_rectangle=(self.x, self.y, self.width,
                                                self.height, self.radius_dp),
                             width=1.1)
        self.bind(pos=self._redraw, size=self._redraw, state=self._redraw)
        self.bind(size=lambda w, s: setattr(w, "text_size", (s[0] - dp(24), None)))
        self._redraw()

    def _show_border(self):
        return self.variant == "ghost"

    def _fill(self):
        down = self.state == "down"
        if self.variant == "primary":
            return C_ACCENT_D if down else C_ACCENT
        if self.variant == "danger":
            return C_DANGER_D if down else C_DANGER
        return C_FIELD_D if down else C_FIELD

    def _redraw(self, *_):
        self._bgr.pos = self.pos
        self._bgr.size = self.size
        self._bdl.rounded_rectangle = (self.x, self.y, self.width,
                                       self.height, self.radius_dp)
        self._bgc.rgba = self._fill()
        self._bdc.rgba = (*C_BORDER, 1) if self._show_border() else (*C_BORDER, 0)


class TabButton(TButton):
    """Pill tab in the top tab bar."""

    def __init__(self, text, **kw):
        self.active_tab = False
        self.radius_dp = dp(19)
        super().__init__(text=text, variant="tab", **kw)
        self.height = dp(38)
        self.font_size = sp(14)
        # size ONCE from the natural texture; never bind texture->width
        # (combined with the size->text_size binding that loops forever,
        # growing the pill without bound — seen in headless screenshots)
        self.texture_update()
        self.width = self.texture_size[0] + dp(30)
        self._redraw()

    def _show_border(self):
        return not self.active_tab

    def _fill(self):
        down = self.state == "down"
        if self.active_tab:
            return C_ACCENT_D if down else C_ACCENT
        return C_FIELD_D if down else C_FIELD

    def set_active(self, on):
        self.active_tab = on
        self.bold = on
        self._redraw()


class TInput(TextInput):
    """Dark rounded text field; background is a generated PNG because
    TextInput draws its text inside canvas.before — a canvas-drawn
    background there would paint OVER the text (verified by bisection)."""

    def __init__(self, **kw):
        super().__init__(**kw)
        n, f = field_bg_paths()
        if n:
            self.background_normal = n
            self.background_active = f
            self.background_disabled = n
            self.border = (16, 16, 16, 16)
        self.foreground_color = C_TEXT
        self.hint_text_color = C_MUTED
        self.cursor_color = C_ACCENT
        self.selection_color = (C_ACCENT[0], C_ACCENT[1], C_ACCENT[2], 0.35)
        self.font_size = sp(15)


class TSpinnerOption(SpinnerOption):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = C_FIELD
        self.color = C_TEXT
        self.font_size = sp(15)
        self.size_hint_y = None
        self.height = dp(46)


class TSpinner(Spinner):
    """Spinner dressed like a ghost button."""

    def __init__(self, **kw):
        kw.setdefault("option_cls", TSpinnerOption)
        kw.setdefault("sync_height", True)
        super().__init__(**kw)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = C_TEXT
        self.font_size = sp(15)
        with self.canvas.before:
            Color(*C_FIELD)
            self._bgr = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
            Color(*C_BORDER)
            self._bdl = Line(rounded_rectangle=(self.x, self.y, self.width,
                                                self.height, dp(12)), width=1.1)
        self.bind(pos=self._redraw, size=self._redraw)
        self._redraw()

    def _redraw(self, *_):
        self._bgr.pos = self.pos
        self._bgr.size = self.size
        self._bdl.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(12))


class TProgress(Widget):
    """Slim rounded progress bar (accent fill)."""

    value = NumericProperty(0)
    max = NumericProperty(100)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint_y = None
        self.height = dp(10)
        with self.canvas:
            Color(*C_FIELD)
            self._track = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])
            Color(*C_ACCENT)
            self._fillr = RoundedRectangle(pos=self.pos, size=(0, self.height),
                                           radius=[dp(5)])
        self.bind(pos=self._redraw, size=self._redraw,
                  value=self._redraw, max=self._redraw)
        self._redraw()

    def _redraw(self, *_):
        self._track.pos = self.pos
        self._track.size = self.size
        frac = 0.0
        if self.max:
            frac = max(0.0, min(1.0, self.value / float(self.max)))
        self._fillr.pos = self.pos
        self._fillr.size = (self.width * frac, self.height)


class Card(BoxLayout):
    """Rounded surface grouping related controls, with an optional title.
    fill=True makes it stretch to the available height instead of
    hugging its content (used by the Log screen)."""

    def __init__(self, title=None, fill=False, **kw):
        super().__init__(orientation="vertical", **kw)
        self.padding = [dp(16), dp(14), dp(16), dp(16)]
        self.spacing = dp(10)
        with self.canvas.before:
            Color(*C_CARD)
            self._bgr = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
            Color(*C_BORDER)
            self._bdl = Line(rounded_rectangle=(self.x, self.y, self.width,
                                                self.height, dp(16)), width=1)
        self.bind(pos=self._redraw, size=self._redraw)
        if fill:
            self.size_hint_y = 1
        else:
            self.size_hint_y = None
            self.bind(minimum_height=self.setter("height"))
        if title:
            t = Label(text=title, font_size=sp(16), bold=True, color=C_TEXT,
                      size_hint_y=None, height=dp(24), halign="left", valign="middle")
            t.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
            self.add_widget(t)

    def _redraw(self, *_):
        self._bgr.pos = self.pos
        self._bgr.size = self.size
        self._bdl.rounded_rectangle = (self.x, self.y, self.width, self.height, dp(16))


class Divider(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.size_hint_y = None
        self.height = dp(1)
        with self.canvas:
            Color(*C_BORDER)
            self._r = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self._r.pos = self.pos
        self._r.size = self.size


# ---------------- small builders ----------------
def L(text, kind="body", **kw):
    styles = {
        "body": dict(font_size=sp(15), color=C_TEXT),
        "sub": dict(font_size=sp(13.5), color=C_SUB),
        "muted": dict(font_size=sp(12.5), color=C_MUTED),
        "h": dict(font_size=sp(17), bold=True, color=C_TEXT),
        "section": dict(font_size=sp(13), bold=True, color=C_ACCENT),
    }
    st = dict(styles.get(kind, styles["body"]))
    if kw.pop("bold", False):
        st["bold"] = True
        st.setdefault("font_size", sp(16))
    kw.setdefault("size_hint_y", None)
    fixed_h = kw.pop("height", None)
    lab = Label(text=text, **st, **kw)
    lab.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
    if fixed_h is not None:
        lab.height = dp(fixed_h)
    else:
        lab.height = dp(24)
        lab.bind(texture_size=lambda w, s: setattr(
            w, "height", max(dp(22), s[1] + dp(2))))
    return lab


def B(text, cb, variant="ghost", strip=True, **kw):
    if strip:
        text = clean_text(text)
    b = TButton(text=text, variant=variant, **kw)
    b.bind(on_release=lambda *_: cb())
    return b


def I(hint="", multiline=False, password=False, height=None, text=""):
    ti = TInput(hint_text=hint, multiline=multiline, password=password, text=text,
                size_hint_y=None, height=dp(height or (120 if multiline else 48)),
                padding=[dp(14), dp(12)])
    return ti


def scroll_page():
    root = BoxLayout(orientation="vertical")
    paint_bg(root, C_BG)
    sv = ScrollView(size_hint=(1, 1), bar_width=dp(4),
                    bar_color=(C_ACCENT[0], C_ACCENT[1], C_ACCENT[2], 0.55),
                    bar_inactive_color=(C_BORDER[0], C_BORDER[1], C_BORDER[2], 0.5),
                    scroll_type=["bars", "content"])
    page = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(14),
                     padding=[dp(14), dp(14), dp(14), dp(22)])
    page.bind(minimum_height=page.setter("height"))
    sv.add_widget(page)
    root.add_widget(sv)
    return root, page


def card(page, title=None):
    c = Card(title=title)
    page.add_widget(c)
    return c


def field_row(label_text):
    row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
    lab = L(label_text)
    lab.size_hint_x = 0.42
    row.add_widget(lab)
    return row



class StudioApp(App):
    title = APP_TITLE

    # ---------- state ----------
    def __init__(self, **kw):
        super().__init__(**kw)
        self.cfg = {}
        self.video = None            # VideoInfo of the current video
        self.work_title = ""
        self.work_desc = ""
        self.work_tags = []
        self.all_results = {}        # video_id -> {code: {...}}
        self.title_cands = []
        self.scan_rows = []
        self._uploader = None
        self._upl_key = None
        self.quota = sc.QuotaStore()
        self.registry = sc.Registry()
        self._log_lines = []

    # ---------- config ----------
    @property
    def cfg_path(self):
        return os.path.join(self.user_data_dir, "yt_studio_pro_cfg.json")

    def load_cfg(self):
        try:
            self.cfg = json.load(open(self.cfg_path, encoding="utf-8"))
        except Exception:
            self.cfg = {}
        self.cfg.setdefault("gemini_model", "gemini-3.5-flash")

    def save_cfg(self):
        try:
            with open(self.cfg_path, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"❌ Lưu cài đặt lỗi: {e}")

    def engine_cfg(self):
        return {"gemini_key": self.cfg.get("gemini_key", ""),
                "openai_key": self.cfg.get("openai_key", ""),
                "gemini_model": self.cfg.get("gemini_model", "gemini-3.5-flash"),
                "youtube_api_key": self.cfg.get("yt_api_key", "")}

    def uploader(self):
        key = (self.cfg.get("oauth_client_id", ""), self.cfg.get("oauth_client_secret", ""))
        if self._uploader is None or self._upl_key != key:
            self._uploader = core.YouTubeUploader(key[0], key[1])
            self._uploader.on_quota = lambda n: Clock.schedule_once(
                lambda dt: (self.quota.add(n), self.refresh_quota()))
            self._upl_key = key
        return self._uploader

    # ---------- ui helpers ----------
    def log(self, msg):
        line = clean_text(msg)
        self._log_lines.append(line)
        if len(self._log_lines) > 400:
            self._log_lines = self._log_lines[-400:]
        def upd(dt):
            if hasattr(self, "log_label"):
                self.log_label.text = "\n".join(self._log_lines[-120:])
        Clock.schedule_once(upd)

    def bg(self, fn, done=None, fail_prefix="❌"):
        def wrap():
            try:
                r = fn()
            except Exception as e:
                traceback.print_exc()
                self.log(f"{fail_prefix} {e}")
                return
            if done:
                Clock.schedule_once(lambda dt: done(r))
        threading.Thread(target=wrap, daemon=True).start()

    def refresh_quota(self):
        if hasattr(self, "quota_label"):
            self.quota_label.text = f"Quota hôm nay: {self.quota.units} / 10.000"

    def goto(self, name):
        names = [n for n, _ in getattr(self, "TABS", [])]
        cur = self.sm.current
        if names and cur in names and name in names and cur != name:
            self.sm.transition.direction = ("left" if names.index(name) > names.index(cur)
                                            else "right")
        self.sm.current = name
        for k, btn in getattr(self, "tab_btns", {}).items():
            btn.set_active(k == name)

    # ---------- build ----------
    def build(self):
        self.load_cfg()
        Window.clearcolor = C_BG
        root = BoxLayout(orientation="vertical")
        paint_bg(root, C_BG)

        # header: title block + quota pill
        header = BoxLayout(size_hint_y=None, height=dp(60),
                           padding=[dp(16), dp(6), dp(14), dp(4)], spacing=dp(10))
        tcol = BoxLayout(orientation="vertical")
        ttl = Label(text=APP_TITLE, font_size=sp(18), bold=True, color=C_TEXT,
                    halign="left", valign="bottom", size_hint_y=None, height=dp(27))
        ttl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        own = Label(text=f"© {OWNER}", font_size=sp(11.5), color=C_MUTED,
                    halign="left", valign="top", size_hint_y=None, height=dp(17))
        own.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        tcol.add_widget(ttl)
        tcol.add_widget(own)
        header.add_widget(tcol)

        pill = BoxLayout(size_hint=(None, None), height=dp(30),
                         padding=[dp(11), 0, dp(12), 0], spacing=dp(7),
                         pos_hint={"center_y": 0.5})
        with pill.canvas.before:
            Color(*C_FIELD)
            pill._bgr = RoundedRectangle(pos=pill.pos, size=pill.size, radius=[dp(15)])
            Color(*C_BORDER)
            pill._bdl = Line(rounded_rectangle=(pill.x, pill.y, pill.width,
                                                pill.height, dp(15)), width=1)

        def pill_redraw(*_):
            pill._bgr.pos = pill.pos
            pill._bgr.size = pill.size
            pill._bdl.rounded_rectangle = (pill.x, pill.y, pill.width, pill.height, dp(15))
        pill.bind(pos=pill_redraw, size=pill_redraw)
        dot = Widget(size_hint=(None, None), size=(dp(8), dp(8)),
                     pos_hint={"center_y": 0.5})
        with dot.canvas:
            Color(*C_GOLD)
            dot._el = Ellipse(pos=dot.pos, size=dot.size)
        dot.bind(pos=lambda w, *_: setattr(w._el, "pos", w.pos),
                 size=lambda w, *_: setattr(w._el, "size", w.size))
        pill.add_widget(dot)
        self.quota_label = Label(text="", font_size=sp(12.5), color=C_SUB,
                                 size_hint=(None, None), height=dp(30),
                                 halign="left", valign="middle")
        self.quota_label.bind(texture_size=lambda w, s: setattr(w, "width", s[0]))
        pill.add_widget(self.quota_label)
        pill.bind(minimum_width=pill.setter("width"))
        header.add_widget(pill)
        root.add_widget(header)
        root.add_widget(Divider())
        self.refresh_quota()

        # pill tab bar
        self.TABS = [("kenh", "Kênh & API"), ("video", "Video"), ("tieude", "Tiêu đề"),
                     ("mota", "Mô tả"), ("dich", "Dịch"), ("day", "Đẩy"),
                     ("doithu", "Đối thủ"), ("log", "Log")]
        tsv = ScrollView(size_hint_y=None, height=dp(54), do_scroll_y=False, bar_width=0)
        trow = BoxLayout(size_hint_x=None, spacing=dp(8),
                         padding=[dp(12), dp(8), dp(12), dp(8)])
        trow.bind(minimum_width=trow.setter("width"))
        self.tab_btns = {}
        for name, label in self.TABS:
            b = TabButton(text=label, size_hint_x=None)
            b.bind(on_release=lambda *_a, n=name: self.goto(n))
            trow.add_widget(b)
            self.tab_btns[name] = b
        tsv.add_widget(trow)
        root.add_widget(tsv)

        self.sm = ScreenManager()
        self.sm.transition = SlideTransition(duration=0.22)
        root.add_widget(self.sm)
        for name, builder in [("kenh", self.scr_kenh), ("video", self.scr_video),
                              ("tieude", self.scr_tieude), ("mota", self.scr_mota),
                              ("dich", self.scr_dich), ("day", self.scr_day),
                              ("doithu", self.scr_doithu), ("log", self.scr_log)]:
            s = Screen(name=name)
            s.add_widget(builder())
            self.sm.add_widget(s)
        self.tab_btns["kenh"].set_active(True)
        self.log(f"{APP_TITLE} iOS v3 — lõi dịch v2.3.5 (Google › Gemini cứu hộ khi bị chặn)")
        return root

    # ---------- Screen 1: channel & API ----------
    def scr_kenh(self):
        root, p = scroll_page()
        c = card(p, "API keys")
        self.in_yt_key = I("YouTube Data API key (đọc thông tin video chính xác)", password=True,
                           text=self.cfg.get("yt_api_key", ""))
        c.add_widget(self.in_yt_key)
        self.in_gem_key = I("Gemini API key (AI + dịch cứu hộ)", password=True,
                            text=self.cfg.get("gemini_key", ""))
        c.add_widget(self.in_gem_key)
        self.in_oai_key = I("OpenAI API key (dự phòng)", password=True,
                            text=self.cfg.get("openai_key", ""))
        c.add_widget(self.in_oai_key)
        row = field_row("Model Gemini:")
        self.sp_model = TSpinner(text=self.cfg.get("gemini_model", "gemini-3.5-flash"),
                                 values=MODELS, size_hint_y=None, height=dp(48))
        row.add_widget(self.sp_model)
        c.add_widget(row)
        c.add_widget(B("💾 Lưu API & cài đặt", self.act_save_cfg, variant="primary"))

        c2 = card(p, "Đăng nhập kênh (OAuth)")
        self.in_cid = I("OAuth Client ID", text=self.cfg.get("oauth_client_id", ""))
        c2.add_widget(self.in_cid)
        self.in_csec = I("OAuth Client Secret", password=True,
                         text=self.cfg.get("oauth_client_secret", ""))
        c2.add_widget(self.in_csec)
        c2.add_widget(B("🔐 Đăng nhập Google (mở Safari)", self.act_login, variant="primary"))
        self.lbl_login = L("Chưa đăng nhập", kind="sub")
        c2.add_widget(self.lbl_login)
        c2.add_widget(B("📋 Copy link đăng nhập", self.act_copy_login_url))
        self.in_paste = I("Nếu Safari không tự quay lại: dán LINK chứa code= vào đây", multiline=True, height=110)
        c2.add_widget(self.in_paste)
        c2.add_widget(B("✅ Dán code xong — hoàn tất đăng nhập", self.act_paste_code))
        c2.add_widget(B("Đăng xuất", self.act_logout))

        c3 = card(p, "Ngách & sản phẩm")
        self.in_niche = I("Ngách kênh (vd: woodworking custom furniture build)",
                          text=self.cfg.get("niche", ""))
        c3.add_widget(self.in_niche)
        self.in_product = I("Sản phẩm / chất liệu / kỹ thuật trong video",
                            text=self.cfg.get("product", ""))
        c3.add_widget(self.in_product)
        Clock.schedule_once(lambda dt: self.refresh_login_label())
        return root

    def refresh_login_label(self):
        try:
            up = self.uploader()
            if up.logged_in:
                self.lbl_login.text = clean_text("✅ Đã đăng nhập (token đã lưu)")
            else:
                self.lbl_login.text = "Chưa đăng nhập"
        except Exception:
            pass

    def act_save_cfg(self):
        self.cfg.update({
            "yt_api_key": self.in_yt_key.text.strip(),
            "gemini_key": self.in_gem_key.text.strip(),
            "openai_key": self.in_oai_key.text.strip(),
            "gemini_model": self.sp_model.text,
            "oauth_client_id": self.in_cid.text.strip(),
            "oauth_client_secret": self.in_csec.text.strip(),
            "niche": self.in_niche.text.strip(),
            "product": self.in_product.text.strip(),
        })
        self._uploader = None
        self.save_cfg()
        self.log("💾 Đã lưu cài đặt")
        self.refresh_login_label()

    def act_login(self):
        self.act_save_cfg()
        up = self.uploader()
        def on_url(url):
            self._login_url = url
            Clock.schedule_once(lambda dt: self.log("🔗 Đã mở Safari để đăng nhập — chọn đúng kênh thương hiệu (Brand Account) nếu được hỏi"))
            open_url(url)
        self.log("🔐 Đang chờ đăng nhập ở Safari… (quay lại app sau khi xong)")
        def work():
            return up.login_ios(log=self.log, on_url=on_url)
        def done(_r):
            try:
                info = up.channel_info()
                self.lbl_login.text = clean_text(f"✅ Kênh: {info.get('title')}")
                self.log(f"✅ Đăng nhập thành công. Kênh: {info.get('title')}")
            except Exception:
                self.lbl_login.text = clean_text("✅ Đã đăng nhập")
                self.log("✅ Đăng nhập thành công")
        self.bg(work, done)

    def act_copy_login_url(self):
        url = getattr(self, "_login_url", "")
        if not url:
            up = self.uploader()
            url = up.auth_url(core.YouTubeUploader.IOS_REDIRECT)
            self._login_url = url
        Clipboard.copy(url)
        self.log("📋 Đã copy link đăng nhập — dán vào Safari/Chrome rồi đăng nhập, xong quay lại app")

    def act_paste_code(self):
        raw = self.in_paste.text.strip()
        code = raw
        if "code=" in raw:
            import urllib.parse as up2
            qs = up2.parse_qs(up2.urlparse(raw).query)
            code = (qs.get("code") or [raw])[0]
        if not code:
            self.log("⚠️ Chưa có code để hoàn tất")
            return
        up = self.uploader()
        self.bg(lambda: up.exchange_code(code),
                lambda _r: (self.refresh_login_label(), self.log("✅ Hoàn tất đăng nhập bằng code")))

    def act_logout(self):
        self.uploader().logout()
        self.refresh_login_label()
        self.log("Đã đăng xuất")


    # ---------- Screen 2: video ----------
    def scr_video(self):
        root, p = scroll_page()
        c = card(p, "Link video")
        c.add_widget(L("Mỗi dòng 1 link, hoặc chỉ 1 link", kind="sub"))
        self.in_links = I("https://youtu.be/...", multiline=True, height=110)
        c.add_widget(self.in_links)
        c.add_widget(B("🔎 Lấy thông tin video", self.act_fetch, variant="primary"))
        c.add_widget(B("⏬ Lấy video mới nhất của kênh tôi", self.act_latest))
        c2 = card(p, "Thông tin video")
        self.lbl_video = L("Chưa có video")
        c2.add_widget(self.lbl_video)
        self.lbl_src = L("", kind="sub")
        c2.add_widget(self.lbl_src)
        return root

    def _set_video(self, v):
        self.video = v
        self.work_title = v.title or ""
        self.work_desc = v.description or ""
        src = core.LANG_BY_CODE.get((v.default_language or "").lower())
        src_txt = f"{src.name_vi} [{src.code}]" if src else (v.default_language or "chưa rõ — tool tự dò khi dịch")
        exist = ", ".join(v.existing_languages) if v.existing_languages else "(chưa đọc được — cần API key hoặc đăng nhập)"
        self.lbl_video.text = (f"{v.title}\nKênh: {v.channel}\nID: {v.video_id}\n"
                               f"Mô tả: {len(v.description or '')} ký tự")
        self.lbl_src.text = f"Ngôn ngữ gốc: {src_txt}\nĐã có trên YouTube: {exist}"
        if hasattr(self, "lbl_dich_info"):
            self.lbl_dich_info.text = self.lbl_video.text
        self.log(f"🎬 Đã lấy video {v.video_id} — {v.title}")

    def act_fetch(self):
        links = [s.strip() for s in self.in_links.text.replace(",", "\n").splitlines() if s.strip()]
        if not links:
            self.log("⚠️ Chưa nhập link video")
            return
        key = self.cfg.get("yt_api_key", "")
        self.bg(lambda: core.fetch_video(links[0], key or None), self._set_video)

    def act_latest(self):
        up = self.uploader()
        def work():
            vid = up.latest_video_id()
            return core.fetch_video(vid, self.cfg.get("yt_api_key", "") or None)
        self.bg(work, self._set_video)

    # ---------- Screen 3: AI titles ----------
    def scr_tieude(self):
        root, p = scroll_page()
        c = card(p, "Cảm xúc chủ đạo")
        c.add_widget(L("Chọn vài cảm xúc để AI bám theo", kind="sub"))
        grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(6))
        grid.bind(minimum_height=grid.setter("height"))
        self.emo_checks = {}
        for key, label, _d in sc.EMOTIONS:
            row = BoxLayout(size_hint_y=None, height=dp(46))
            cb = CheckBox(size_hint_x=None, width=dp(40), color=(0.55, 0.72, 1, 1))
            row.add_widget(cb)
            row.add_widget(L(clean_text(label), kind="sub"))
            grid.add_widget(row)
            self.emo_checks[key] = cb
        c.add_widget(grid)
        c.add_widget(B("✨ Tạo 3 tiêu đề AI", self.act_gen_titles, variant="primary"))
        self.cand_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        self.cand_box.bind(minimum_height=self.cand_box.setter("height"))
        p.add_widget(self.cand_box)
        c2 = card(p, "Tiêu đề đang dùng")
        self.in_title = I("Tiêu đề", multiline=True, height=80)
        c2.add_widget(self.in_title)
        self.lbl_chars = L("0 ký tự", kind="muted")
        c2.add_widget(self.lbl_chars)
        self.in_title.bind(text=lambda _w, v: setattr(self.lbl_chars, "text", f"{len(v)} ký tự"))
        c2.add_widget(B("✅ Dùng tiêu đề này", self.act_apply_title, variant="primary"))
        return root

    def _emotions(self):
        return [k for k, cb in self.emo_checks.items() if cb.active]

    def act_gen_titles(self):
        if not self.video:
            self.log("⚠️ Chưa có video — sang tab Video lấy thông tin trước")
            return
        cfg = self.engine_cfg()
        orig = self.video.title
        prod, niche, emos = self.cfg.get("product", ""), self.cfg.get("niche", ""), self._emotions()
        self.log("✨ Đang tạo 3 tiêu đề…")
        def done(cands):
            self.title_cands = cands
            self.cand_box.clear_widgets()
            for i, c in enumerate(cands):
                txt = f"{i+1}. {c['title']}\nCTR dự đoán {c.get('ctr', 0)}% · {c.get('vi', '')} · Hook: {c.get('hook', '')}"
                self.cand_box.add_widget(B(txt, lambda c=c: self._pick_title(c),
                                           height=76, halign="left", strip=False))
            self.log(f"🏆 Đã có {len(cands)} phương án tiêu đề")
        self.bg(lambda: sc.gen_titles(cfg, orig, prod, emos, niche, log=self.log), done)

    def _pick_title(self, c):
        self.in_title.text = c["title"]

    def act_apply_title(self):
        self.work_title = self.in_title.text.strip()
        self.log(f"✅ Đã chốt tiêu đề ({len(self.work_title)} ký tự)")

    # ---------- Screen 4: description & tags ----------
    def scr_mota(self):
        root, p = scroll_page()
        c = card(p, "Mô tả & Tags")
        c.add_widget(B("📝 AI viết mô tả + tags + chapters", self.act_gen_desc, variant="primary"))
        c.add_widget(L("Mô tả đang dùng:", kind="sub"))
        self.in_desc = I("Mô tả", multiline=True, height=220)
        c.add_widget(self.in_desc)
        c.add_widget(L("Tags (cách nhau bằng dấu phẩy):", kind="sub"))
        self.in_tags = I("tags", multiline=True, height=80)
        c.add_widget(self.in_tags)
        c.add_widget(B("✅ Dùng mô tả + tags này", self.act_apply_desc, variant="primary"))
        return root

    def act_gen_desc(self):
        cfg = self.engine_cfg()
        title = self.work_title or (self.video.title if self.video else "")
        if not title:
            self.log("⚠️ Chưa có tiêu đề/video")
            return
        prod, emos = self.cfg.get("product", ""), self._emotions()
        orig = self.video.description if self.video else ""
        self.log("📝 Đang viết mô tả…")
        def done(d):
            self.in_desc.text = d["description"]
            self.in_tags.text = ", ".join(d["tags"])
            self.work_desc = d["description"]
            self.work_tags = d["tags"]
            self.log(f"✅ Mô tả {len(d['description'])} ký tự · {len(d['tags'])} tags")
        self.bg(lambda: sc.gen_description(cfg, title, prod, emos, orig, log=self.log), done)

    def act_apply_desc(self):
        self.work_desc = self.in_desc.text
        self.work_tags = [t.strip() for t in self.in_tags.text.split(",") if t.strip()]
        self.log("✅ Đã chốt mô tả + tags")

    # ---------- Screen 5: translate ----------
    def scr_dich(self):
        root, p = scroll_page()
        c0 = card(p, "Video")
        self.lbl_dich_info = L("Chưa có video")
        c0.add_widget(self.lbl_dich_info)
        c = card(p, "Cấu hình dịch")
        row = field_row("Máy dịch:")
        self.sp_engine = TSpinner(text="google", values=["google", "gemini", "openai"],
                                  size_hint_y=None, height=dp(48))
        row.add_widget(self.sp_engine)
        c.add_widget(row)
        row2 = field_row("Bộ ngôn ngữ:")
        self.sp_preset = TSpinner(text="Preset 40",
                                  values=["Preset 40", "Preset 20", "Preset 12", "Tất cả 84", "Tùy chọn"],
                                  size_hint_y=None, height=dp(48))
        row2.add_widget(self.sp_preset)
        c.add_widget(row2)
        self.in_custom = I("Mã tùy chọn, cách nhau bằng dấu phẩy (vd: ja,ko,fr) — chỉ khi chọn 'Tùy chọn'")
        c.add_widget(self.in_custom)
        row3 = BoxLayout(size_hint_y=None, height=dp(40))
        self.cb_skip = CheckBox(size_hint_x=None, width=dp(40), active=True,
                                color=(0.55, 0.72, 1, 1))
        row3.add_widget(self.cb_skip)
        row3.add_widget(L("Bỏ qua ngôn ngữ ĐÃ CÓ trên YouTube"))
        c.add_widget(row3)
        self.pb = TProgress(max=100, value=0)
        c.add_widget(self.pb)
        c.add_widget(B("🚀 BẮT ĐẦU DỊCH", self.act_translate, variant="primary", height=54))
        self.lbl_dich_done = L("", kind="sub")
        c.add_widget(self.lbl_dich_done)
        c.add_widget(B("💾 Xuất TXT vào thư mục app", self.act_export))
        return root

    def _targets(self):
        name = self.sp_preset.text
        if name == "Tất cả 84":
            codes = [l.code for l in LANGUAGES]
        elif name == "Tùy chọn":
            codes = [c.strip() for c in self.in_custom.text.split(",") if c.strip()]
        else:
            codes = {"Preset 40": sc.PRESET_40, "Preset 20": sc.PRESET_20,
                     "Preset 12": sc.PRESET_12}[name]
        out = []
        src = (self.video.default_language or "").lower() if self.video else ""
        existing = set()
        if self.cb_skip.active and self.video:
            existing = {core._norm_lang(c) for c in self.video.existing_languages}
        for c in codes:
            lang = LANG_BY_CODE.get(c if c != "he" else "iw") or LANG_BY_CODE.get(c.lower())
            if not lang:
                continue
            if src and core._norm_lang(lang.code) == core._norm_lang(src):
                continue
            if core._norm_lang(lang.code) in existing:
                continue
            out.append(lang)
        return out

    def act_translate(self):
        if not self.video:
            self.log("⚠️ Chưa có video")
            return
        targets = self._targets()
        if not targets:
            self.log("⚠️ Không còn ngôn ngữ nào cần dịch")
            return
        title = self.work_title or self.video.title
        desc = self.work_desc or self.video.description
        engine = self.sp_engine.text
        cfg = self.engine_cfg()
        vid = self.video.video_id
        total = len(targets)
        self.log(f"🌍 Dịch {total} ngôn ngữ bằng {engine} (Google lỗi sẽ có Gemini cứu hộ)…")
        def prog(done_n, tot, lang):
            Clock.schedule_once(lambda dt: setattr(self.pb, "value", (done_n * 100 / max(tot, 1))))
        def work():
            return core.translate_many(title, desc, targets, engine, cfg,
                                       self.video.default_language or "auto",
                                       log=self.log, on_progress=prog)
        def done(results):
            self.all_results[vid] = results
            self.pb.value = 100
            self.lbl_dich_done.text = clean_text(f"✅ Đã dịch {len(results)}/{total} ngôn ngữ — sang tab Đẩy để đăng lên kênh")
            self.log(f"🌍 Xong: {len(results)}/{total} ngôn ngữ")
        self.bg(work, done)

    def act_export(self):
        if not self.video or self.video.video_id not in self.all_results:
            self.log("⚠️ Chưa có kết quả dịch để xuất")
            return
        out_dir = os.path.join(self.user_data_dir, "exports")
        os.makedirs(out_dir, exist_ok=True)
        results = self.all_results[self.video.video_id]
        v = self.video
        self.bg(lambda: core.export_video_results(v, results, out_dir, src_title=v.title, src_desc=v.description),
                lambda r: self.log(f"💾 Đã xuất TXT vào thư mục app: {out_dir}"))


    # ---------- Screen 6: push ----------
    def scr_day(self):
        root, p = scroll_page()
        c = card(p, "Đẩy lên kênh")
        c.add_widget(L("Cần đăng nhập ở tab Kênh & API", kind="sub"))
        c.add_widget(B("🌍 Đẩy bản dịch (tiêu đề + mô tả đa ngôn ngữ)", self.act_push_loc, variant="primary"))
        c.add_widget(B("✏️ Đẩy tiêu đề + mô tả + tags (tiếng Anh)", self.act_push_snippet))
        self.in_comment = I("Bình luận đầu tiên (để trống = tự tạo)", multiline=True, height=80)
        c.add_widget(self.in_comment)
        c.add_widget(B("💬 Ghim bình luận đầu tiên", self.act_comment))
        c2 = card(p, "1-CLICK toàn bộ quy trình")
        c2.add_widget(L("AI tiêu đề › AI mô tả › dịch › đẩy tất cả", kind="sub"))
        c2.add_widget(B("🔴 1-CLICK CHẠY TOÀN BỘ", self.act_oneclick, variant="danger", height=54))
        return root

    def _need_login(self):
        up = self.uploader()
        if not up.logged_in:
            self.log("⚠️ Chưa đăng nhập kênh — sang tab Kênh & API")
            return None
        return up

    def act_push_loc(self):
        up = self._need_login()
        if not up or not self.video:
            return
        results = self.all_results.get(self.video.video_id)
        if not results:
            self.log("⚠️ Chưa có kết quả dịch — sang tab Dịch trước")
            return
        v = self.video
        backup = os.path.join(self.user_data_dir, "backups")
        self.bg(lambda: up.push_video(v, results, backup_dir=backup, log=self.log),
                lambda _r: self.log("✅ Đã đẩy bản dịch lên kênh"))

    def act_push_snippet(self):
        up = self._need_login()
        if not up or not self.video:
            return
        vid = self.video.video_id
        t, d, tags = self.work_title or None, self.work_desc or None, self.work_tags or None
        self.bg(lambda: up.update_snippet(vid, title=t, description=d, tags=tags, log=self.log),
                lambda _r: self.log("✅ Đã đẩy tiêu đề/mô tả lên kênh"))

    def act_comment(self):
        up = self._need_login()
        if not up or not self.video:
            return
        text = self.in_comment.text.strip() or "👇 Xem thêm các video hay khác trên kênh nhé!"
        vid = self.video.video_id
        self.bg(lambda: up.post_comment(vid, text, log=self.log),
                lambda _r: self.log("✅ Đã đăng bình luận"))

    def act_oneclick(self):
        up = self._need_login()
        if not up or not self.video:
            if not self.video:
                self.log("⚠️ Chưa có video")
            return
        cfg = self.engine_cfg()
        v = self.video
        emos = self._emotions()
        prod, niche = self.cfg.get("product", ""), self.cfg.get("niche", "")
        targets = self._targets()
        backup = os.path.join(self.user_data_dir, "backups")
        def work():
            self.log("🔴 1-CLICK bắt đầu…")
            cands = sc.gen_titles(cfg, v.title, prod, emos, niche, log=self.log)
            title = cands[0]["title"]
            self.log(f"1️⃣ Tiêu đề AI: {title}")
            d = sc.gen_description(cfg, title, prod, emos, v.description, log=self.log)
            self.log(f"2️⃣ Mô tả AI: {len(d['description'])} ký tự · {len(d['tags'])} tags")
            results = core.translate_many(title, d["description"], targets,
                                          self.sp_engine.text, cfg,
                                          v.default_language or "auto", log=self.log)
            self.all_results[v.video_id] = results
            Clock.schedule_once(lambda dt: setattr(self, "work_title", title))
            self.work_title, self.work_desc, self.work_tags = title, d["description"], d["tags"]
            self.log(f"3️⃣ Dịch xong {len(results)}/{len(targets)} ngôn ngữ")
            up.update_snippet(v.video_id, title=title, description=d["description"],
                              tags=d["tags"], log=self.log)
            up.push_video(v, results, backup_dir=backup, log=self.log)
            return True
        self.bg(work, lambda _r: self.log("🏁 1-CLICK HOÀN TẤT"))

    # ---------- Screen 7: competitors & health ----------
    def scr_doithu(self):
        root, p = scroll_page()
        c = card(p, "Đối thủ & ý tưởng")
        c.add_widget(L("@handle đối thủ (mỗi dòng 1 handle)", kind="sub"))
        self.in_handles = I("@MrBeast", multiline=True, height=90,
                            text=self.cfg.get("competitors", ""))
        c.add_widget(self.in_handles)
        c.add_widget(B("🔍 Quét đối thủ (video đang nổ)", self.act_scan, variant="primary"))
        c.add_widget(B("❤️ Kiểm tra sức khỏe video hiện tại (24H)", self.act_health))
        c.add_widget(B("💡 Tạo ý tưởng từ video đang nổ", self.act_ideas))
        c2 = card(p, "Kết quả")
        self.lbl_scan = L("")
        c2.add_widget(self.lbl_scan)
        return root

    def act_scan(self):
        up = self._need_login()
        if not up:
            return
        handles = [h.strip() for h in self.in_handles.text.replace(",", "\n").splitlines() if h.strip()]
        if not handles:
            self.log("⚠️ Chưa nhập handle đối thủ")
            return
        self.cfg["competitors"] = self.in_handles.text
        self.save_cfg()
        def done(rows):
            self.scan_rows = rows
            lines = []
            for r in rows[:15]:
                fire = "NỔ · " if r.get("exploding") else ""
                lines.append(f"{fire}[{r.get('channel', '')}] {r.get('title', '')}\n"
                             f"   {r.get('views', 0):,} views · {r.get('vph', 0)}/giờ")
            self.lbl_scan.text = "\n".join(lines) or "(không có dữ liệu)"
            self.log(f"🔍 Quét xong: {len(rows)} video")
        self.bg(lambda: sc.scan_competitors(up, handles, log=self.log), done)

    def act_health(self):
        up = self._need_login()
        if not up or not self.video:
            return
        vid = self.video.video_id
        def done(h):
            s = h.get("video", {})
            self.lbl_scan.text = (f"{s.get('title', '')}\n{h.get('views', 0):,} views · "
                                  f"{h.get('vph', 0)} views/giờ · tuổi {h.get('age_h', 0)} giờ")
            self.log("❤️ Đã kiểm tra sức khỏe video")
        self.bg(lambda: sc.health_check(up, vid), done)

    def act_ideas(self):
        cfg = self.engine_cfg()
        hits = [r.get("title", "") for r in self.scan_rows]
        niche = self.cfg.get("niche", "")
        def done(ideas):
            self.lbl_scan.text = "\n".join(f"{i['idea']}\n   {i.get('why', '')}" for i in ideas)
            self.log(f"💡 Đã tạo {len(ideas)} ý tưởng")
        self.bg(lambda: sc.gen_ideas(cfg, niche, hits, log=self.log), done)

    # ---------- Screen 8: log ----------
    def scr_log(self):
        root = BoxLayout(orientation="vertical")
        paint_bg(root, C_BG)
        wrap = BoxLayout(orientation="vertical", padding=[dp(14), dp(14), dp(14), dp(14)])
        c = Card(fill=True)
        sv = ScrollView(size_hint=(1, 1))
        self.log_label = Label(text="", size_hint_y=None, halign="left", valign="top",
                               color=C_SUB, font_size=sp(13),
                               padding=[dp(2), dp(2)])
        self.log_label.bind(texture_size=lambda w, s: setattr(w, "height", s[1]))
        self.log_label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        sv.add_widget(self.log_label)
        c.add_widget(sv)
        wrap.add_widget(c)
        root.add_widget(wrap)
        btn_row = BoxLayout(size_hint_y=None, height=dp(50),
                            padding=[dp(14), 0, dp(14), dp(10)])
        btn_row.add_widget(B("🧹 Xóa log", lambda: (self._log_lines.clear(), setattr(self.log_label, "text", ""))))
        root.add_widget(btn_row)
        return root


if __name__ == "__main__":
    StudioApp().run()
