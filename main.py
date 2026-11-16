# -*- coding: utf-8 -*-
"""
YT Studio Pro — iOS (Kivy)
Port of the desktop YT Studio Pro (PySide6) to iOS. Same cores (ytb_core /
studio_core, v2.3.5 logic incl. Google->Gemini translation rescue), mobile UI.
Copyright: Nguyễn Đình Hà.
"""
import os, sys, json, threading, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.checkbox import CheckBox
from kivy.uix.progressbar import ProgressBar

import ytb_core as core
import studio_core as sc
from ytb_core import LANGUAGES, LANG_BY_CODE

APP_TITLE = "YT Studio Pro"
OWNER = "Nguyễn Đình Hà"
MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.8-pro"]


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


def L(text, **kw):
    kw.setdefault("size_hint_y", None)
    kw.setdefault("height", dp(24))
    kw.setdefault("halign", "left")
    kw.setdefault("valign", "middle")
    lab = Label(text=text, **kw)
    lab.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
    return lab


def B(text, cb, **kw):
    kw.setdefault("size_hint_y", None)
    kw.setdefault("height", dp(46))
    b = Button(text=text, **kw)
    b.bind(on_release=lambda *_: cb())
    return b


def I(hint="", multiline=False, password=False, height=None, text=""):
    ti = TextInput(hint_text=hint, multiline=multiline, password=password, text=text,
                   size_hint_y=None, height=dp(height or (120 if multiline else 44)),
                   padding=[dp(8), dp(10)])
    return ti


def scroll_page():
    root = BoxLayout(orientation="vertical")
    sv = ScrollView(size_hint=(1, 1))
    page = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8),
                     padding=[dp(10), dp(10), dp(10), dp(10)])
    page.bind(minimum_height=page.setter("height"))
    sv.add_widget(page)
    root.add_widget(sv)
    return root, page


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
        line = str(msg)
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
        self.sm.current = name

    # ---------- build ----------
    def build(self):
        self.load_cfg()
        root = BoxLayout(orientation="vertical")
        header = BoxLayout(size_hint_y=None, height=dp(48), padding=[dp(10), dp(4)],
                           spacing=dp(8))
        header.add_widget(L(f"{APP_TITLE} · © {OWNER}", bold=True))
        self.quota_label = L("")
        header.add_widget(self.quota_label)
        root.add_widget(header)
        self.refresh_quota()

        tabs = [("kenh", "Kênh & API"), ("video", "Video"), ("tieude", "Tiêu đề"),
                ("mota", "Mô tả"), ("dich", "Dịch"), ("day", "Đẩy"),
                ("doithu", "Đối thủ"), ("log", "Log")]
        tsv = ScrollView(size_hint_y=None, height=dp(48), do_scroll_y=False)
        trow = BoxLayout(size_hint_x=None, spacing=dp(4), padding=[dp(4), dp(2)])
        trow.bind(minimum_width=trow.setter("width"))
        for name, label in tabs:
            b = Button(text=label, size_hint_x=None, width=dp(96), height=dp(42))
            b.bind(on_release=lambda *_a, n=name: self.goto(n))
            trow.add_widget(b)
        tsv.add_widget(trow)
        root.add_widget(tsv)

        self.sm = ScreenManager()
        root.add_widget(self.sm)
        for name, builder in [("kenh", self.scr_kenh), ("video", self.scr_video),
                              ("tieude", self.scr_tieude), ("mota", self.scr_mota),
                              ("dich", self.scr_dich), ("day", self.scr_day),
                              ("doithu", self.scr_doithu), ("log", self.scr_log)]:
            s = Screen(name=name)
            s.add_widget(builder())
            self.sm.add_widget(s)
        self.log(f"{APP_TITLE} iOS v1.0 — lõi dịch v2.3.5 (Google → Gemini cứu hộ khi bị chặn)")
        return root

    # ---------- Screen 1: channel & API ----------
    def scr_kenh(self):
        root, p = scroll_page()
        p.add_widget(L("API keys", bold=True))
        self.in_yt_key = I("YouTube Data API key (đọc thông tin video chính xác)", password=True,
                           text=self.cfg.get("yt_api_key", ""))
        p.add_widget(self.in_yt_key)
        self.in_gem_key = I("Gemini API key (AI + dịch cứu hộ)", password=True,
                            text=self.cfg.get("gemini_key", ""))
        p.add_widget(self.in_gem_key)
        self.in_oai_key = I("OpenAI API key (dự phòng)", password=True,
                            text=self.cfg.get("openai_key", ""))
        p.add_widget(self.in_oai_key)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        row.add_widget(L("Model Gemini:"))
        self.sp_model = Spinner(text=self.cfg.get("gemini_model", "gemini-3.5-flash"),
                                values=MODELS, size_hint_y=None, height=dp(44))
        row.add_widget(self.sp_model)
        p.add_widget(row)
        p.add_widget(B("💾 Lưu API & cài đặt", self.act_save_cfg))

        p.add_widget(L("Đăng nhập kênh (OAuth)", bold=True))
        self.in_cid = I("OAuth Client ID", text=self.cfg.get("oauth_client_id", ""))
        p.add_widget(self.in_cid)
        self.in_csec = I("OAuth Client Secret", password=True,
                         text=self.cfg.get("oauth_client_secret", ""))
        p.add_widget(self.in_csec)
        p.add_widget(B("🔐 Đăng nhập Google (mở Safari)", self.act_login))
        self.lbl_login = L("Chưa đăng nhập")
        p.add_widget(self.lbl_login)
        p.add_widget(B("📋 Copy link đăng nhập", self.act_copy_login_url))
        self.in_paste = I("Nếu Safari không tự quay lại: dán LINK chứa code= vào đây", multiline=True, height=110)
        p.add_widget(self.in_paste)
        p.add_widget(B("✅ Dán code xong — hoàn tất đăng nhập", self.act_paste_code))
        p.add_widget(B("Đăng xuất", self.act_logout))

        p.add_widget(L("Ngách & sản phẩm", bold=True))
        self.in_niche = I("Ngách kênh (vd: woodworking custom furniture build)",
                          text=self.cfg.get("niche", ""))
        p.add_widget(self.in_niche)
        self.in_product = I("Sản phẩm / chất liệu / kỹ thuật trong video",
                            text=self.cfg.get("product", ""))
        p.add_widget(self.in_product)
        Clock.schedule_once(lambda dt: self.refresh_login_label())
        return root

    def refresh_login_label(self):
        try:
            up = self.uploader()
            if up.logged_in:
                self.lbl_login.text = "✅ Đã đăng nhập (token đã lưu)"
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
                self.lbl_login.text = f"✅ Kênh: {info.get('title')}"
                self.log(f"✅ Đăng nhập thành công. Kênh: {info.get('title')}")
            except Exception:
                self.lbl_login.text = "✅ Đã đăng nhập"
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
        p.add_widget(L("Link video (mỗi dòng 1 link, hoặc 1 link)", bold=True))
        self.in_links = I("https://youtu.be/...", multiline=True, height=110)
        p.add_widget(self.in_links)
        p.add_widget(B("🔎 Lấy thông tin video", self.act_fetch))
        p.add_widget(B("⏬ Lấy video mới nhất của kênh tôi", self.act_latest))
        self.lbl_video = L("Chưa có video")
        p.add_widget(self.lbl_video)
        self.lbl_src = L("")
        p.add_widget(self.lbl_src)
        return root

    def _set_video(self, v):
        self.video = v
        self.work_title = v.title or ""
        self.work_desc = v.description or ""
        src = core.LANG_BY_CODE.get((v.default_language or "").lower())
        src_txt = f"{src.name_vi} [{src.code}]" if src else (v.default_language or "chưa rõ — tool tự dò khi dịch")
        exist = ", ".join(v.existing_languages) if v.existing_languages else "(chưa đọc được — cần API key hoặc đăng nhập)"
        self.lbl_video.text = (f"🎬 {v.title}\nKênh: {v.channel}\nID: {v.video_id}\n"
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
        p.add_widget(L("Cảm xúc chủ đạo (chọn vài cái)", bold=True))
        grid = GridLayout(cols=2, size_hint_y=None, spacing=dp(4))
        grid.bind(minimum_height=grid.setter("height"))
        self.emo_checks = {}
        for key, label, _d in sc.EMOTIONS:
            row = BoxLayout(size_hint_y=None, height=dp(36))
            cb = CheckBox(size_hint_x=None, width=dp(40))
            row.add_widget(cb)
            row.add_widget(L(label))
            grid.add_widget(row)
            self.emo_checks[key] = cb
        p.add_widget(grid)
        p.add_widget(B("✨ Tạo 3 tiêu đề AI", self.act_gen_titles))
        self.cand_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6))
        self.cand_box.bind(minimum_height=self.cand_box.setter("height"))
        p.add_widget(self.cand_box)
        p.add_widget(L("Tiêu đề đang dùng:", bold=True))
        self.in_title = I("Tiêu đề", multiline=True, height=80)
        p.add_widget(self.in_title)
        self.lbl_chars = L("0 ký tự")
        p.add_widget(self.lbl_chars)
        self.in_title.bind(text=lambda _w, v: setattr(self.lbl_chars, "text", f"{len(v)} ký tự"))
        p.add_widget(B("✅ Dùng tiêu đề này", self.act_apply_title))
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
                self.cand_box.add_widget(B(txt, lambda c=c: self._pick_title(c), height=76))
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
        p.add_widget(B("📝 AI viết mô tả + tags + chapters", self.act_gen_desc))
        p.add_widget(L("Mô tả đang dùng:", bold=True))
        self.in_desc = I("Mô tả", multiline=True, height=220)
        p.add_widget(self.in_desc)
        p.add_widget(L("Tags (cách nhau bằng dấu phẩy):", bold=True))
        self.in_tags = I("tags", multiline=True, height=80)
        p.add_widget(self.in_tags)
        p.add_widget(B("✅ Dùng mô tả + tags này", self.act_apply_desc))
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
        self.lbl_dich_info = L("Chưa có video")
        p.add_widget(self.lbl_dich_info)
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        row.add_widget(L("Máy dịch:"))
        self.sp_engine = Spinner(text="google", values=["google", "gemini", "openai"],
                                 size_hint_y=None, height=dp(44))
        row.add_widget(self.sp_engine)
        p.add_widget(row)
        row2 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        row2.add_widget(L("Bộ ngôn ngữ:"))
        self.sp_preset = Spinner(text="Preset 40",
                                 values=["Preset 40", "Preset 20", "Preset 12", "Tất cả 84", "Tùy chọn"],
                                 size_hint_y=None, height=dp(44))
        row2.add_widget(self.sp_preset)
        p.add_widget(row2)
        self.in_custom = I("Mã tùy chọn, cách nhau bằng dấu phẩy (vd: ja,ko,fr) — chỉ khi chọn 'Tùy chọn'")
        p.add_widget(self.in_custom)
        row3 = BoxLayout(size_hint_y=None, height=dp(40))
        self.cb_skip = CheckBox(size_hint_x=None, width=dp(40), active=True)
        row3.add_widget(self.cb_skip)
        row3.add_widget(L("Bỏ qua ngôn ngữ ĐÃ CÓ trên YouTube"))
        p.add_widget(row3)
        self.pb = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(18))
        p.add_widget(self.pb)
        p.add_widget(B("🚀 BẮT ĐẦU DỊCH", self.act_translate))
        self.lbl_dich_done = L("")
        p.add_widget(self.lbl_dich_done)
        p.add_widget(B("💾 Xuất TXT vào thư mục app", self.act_export))
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
            self.lbl_dich_done.text = f"✅ Đã dịch {len(results)}/{total} ngôn ngữ — sang tab Đẩy để đăng lên kênh"
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
        p.add_widget(L("Đẩy lên kênh (cần đăng nhập ở tab Kênh & API)", bold=True))
        p.add_widget(B("🌍 Đẩy bản dịch (tiêu đề + mô tả đa ngôn ngữ)", self.act_push_loc))
        p.add_widget(B("✏️ Đẩy tiêu đề + mô tả + tags (tiếng Anh)", self.act_push_snippet))
        self.in_comment = I("Bình luận đầu tiên (để trống = tự tạo)", multiline=True, height=80)
        p.add_widget(self.in_comment)
        p.add_widget(B("💬 Ghim bình luận đầu tiên", self.act_comment))
        p.add_widget(L("1-CLICK: AI tiêu đề → AI mô tả → dịch → đẩy tất cả", bold=True))
        p.add_widget(B("🔴 1-CLICK CHẠY TOÀN BỘ", self.act_oneclick))
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
        p.add_widget(L("@handle đối thủ (mỗi dòng 1 handle)", bold=True))
        self.in_handles = I("@MrBeast", multiline=True, height=90,
                            text=self.cfg.get("competitors", ""))
        p.add_widget(self.in_handles)
        p.add_widget(B("🔍 Quét đối thủ (video đang nổ)", self.act_scan))
        p.add_widget(B("❤️ Kiểm tra sức khỏe video hiện tại (24H)", self.act_health))
        p.add_widget(B("💡 Tạo ý tưởng từ video đang nổ", self.act_ideas))
        self.lbl_scan = L("", height=600)
        p.add_widget(self.lbl_scan)
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
                fire = "💥 NỔ " if r.get("exploding") else ""
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
            self.lbl_scan.text = (f"❤️ {s.get('title', '')}\n{h.get('views', 0):,} views · "
                                  f"{h.get('vph', 0)} views/giờ · tuổi {h.get('age_h', 0)} giờ")
            self.log("❤️ Đã kiểm tra sức khỏe video")
        self.bg(lambda: sc.health_check(up, vid), done)

    def act_ideas(self):
        cfg = self.engine_cfg()
        hits = [r.get("title", "") for r in self.scan_rows]
        niche = self.cfg.get("niche", "")
        def done(ideas):
            self.lbl_scan.text = "\n".join(f"💡 {i['idea']}\n   {i.get('why', '')}" for i in ideas)
            self.log(f"💡 Đã tạo {len(ideas)} ý tưởng")
        self.bg(lambda: sc.gen_ideas(cfg, niche, hits, log=self.log), done)

    # ---------- Screen 8: log ----------
    def scr_log(self):
        root = BoxLayout(orientation="vertical")
        sv = ScrollView(size_hint=(1, 1))
        self.log_label = Label(text="", size_hint_y=None, halign="left", valign="top",
                               padding=[dp(10), dp(10)])
        self.log_label.bind(texture_size=lambda w, s: setattr(w, "height", s[1]))
        self.log_label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        sv.add_widget(self.log_label)
        root.add_widget(sv)
        root.add_widget(B("🧹 Xóa log", lambda: (self._log_lines.clear(), setattr(self.log_label, "text", ""))))
        return root


if __name__ == "__main__":
    StudioApp().run()
