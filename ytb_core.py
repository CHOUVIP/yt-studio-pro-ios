# -*- coding: utf-8 -*-
"""
YT Language Translator Pro - Core
Copyright (c) 2026 Nguyen Dinh Ha. All Rights Reserved.
Ban quyen thuoc ve Nguyen Dinh Ha.
"""
import os, re, json, html, time, urllib.parse
from dataclasses import dataclass, field, asdict

COPYRIGHT = "© 2026 Nguyễn Đình Hà — All Rights Reserved"
AUTHOR = "Nguyễn Đình Hà"
APP_NAME = "YT Studio Pro"
VERSION = "2.3.5"

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".yt_lang_translator_pro.json")

def load_config():
    if os.path.exists(CONFIG_PATH):
        try: return json.load(open(CONFIG_PATH, encoding="utf-8"))
        except Exception: return {}
    return {}

def save_config(cfg):
    try: json.dump(cfg, open(CONFIG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception: pass

# code, English name, Vietnamese name, flag, Google Translate code ('' = same as code base)
_RAW = [
('af', 'Afrikaans', 'Tiếng Afrikaans', '🇿🇦', 'af'),
('am', 'Amharic', 'Tiếng Amharic', '🇪🇹', 'am'),
('ar', 'Arabic', 'Tiếng Ả Rập', '🇸🇦', 'ar'),
('as', 'Assamese', 'Tiếng Assam', '🇮🇳', 'as'),
('az', 'Azerbaijani', 'Tiếng Azerbaijan', '🇦🇿', 'az'),
('be', 'Belarusian', 'Tiếng Belarus', '🇧🇾', 'be'),
('bg', 'Bulgarian', 'Tiếng Bulgaria', '🇧🇬', 'bg'),
('bn', 'Bangla', 'Tiếng Bengali', '🇧🇩', 'bn'),
('bs', 'Bosnian', 'Tiếng Bosnia', '🇧🇦', 'bs'),
('ca', 'Catalan', 'Tiếng Catalan', '🇪🇸', 'ca'),
('cs', 'Czech', 'Tiếng Séc', '🇨🇿', 'cs'),
('da', 'Danish', 'Tiếng Đan Mạch', '🇩🇰', 'da'),
('de', 'German', 'Tiếng Đức', '🇩🇪', 'de'),
('el', 'Greek', 'Tiếng Hy Lạp', '🇬🇷', 'el'),
('en', 'English', 'Tiếng Anh', '🇺🇸', 'en'),
('en-GB', 'English (United Kingdom)', 'Tiếng Anh (Anh)', '🇬🇧', 'en'),
('en-IN', 'English (India)', 'Tiếng Anh (Ấn Độ)', '🇮🇳', 'en'),
('es', 'Spanish', 'Tiếng Tây Ban Nha', '🇪🇸', 'es'),
('es-419', 'Spanish (Latin America)', 'Tiếng Tây Ban Nha (Mỹ Latinh)', '🌎', 'es'),
('es-US', 'Spanish (United States)', 'Tiếng Tây Ban Nha (Mỹ)', '🇺🇸', 'es'),
('et', 'Estonian', 'Tiếng Estonia', '🇪🇪', 'et'),
('eu', 'Basque', 'Tiếng Basque', '🇪🇸', 'eu'),
('fa', 'Persian', 'Tiếng Ba Tư', '🇮🇷', 'fa'),
('fi', 'Finnish', 'Tiếng Phần Lan', '🇫🇮', 'fi'),
('fil', 'Filipino', 'Tiếng Filipino', '🇵🇭', 'fil'),
('fr', 'French', 'Tiếng Pháp', '🇫🇷', 'fr'),
('fr-CA', 'French (Canada)', 'Tiếng Pháp (Canada)', '🇨🇦', 'fr'),
('gl', 'Galician', 'Tiếng Galicia', '🇪🇸', 'gl'),
('gu', 'Gujarati', 'Tiếng Gujarati', '🇮🇳', 'gu'),
('hi', 'Hindi', 'Tiếng Hindi', '🇮🇳', 'hi'),
('hr', 'Croatian', 'Tiếng Croatia', '🇭🇷', 'hr'),
('hu', 'Hungarian', 'Tiếng Hungary', '🇭🇺', 'hu'),
('hy', 'Armenian', 'Tiếng Armenia', '🇦🇲', 'hy'),
('id', 'Indonesian', 'Tiếng Indonesia', '🇮🇩', 'id'),
('is', 'Icelandic', 'Tiếng Iceland', '🇮🇸', 'is'),
('it', 'Italian', 'Tiếng Ý', '🇮🇹', 'it'),
('iw', 'Hebrew', 'Tiếng Do Thái', '🇮🇱', 'iw'),
('ja', 'Japanese', 'Tiếng Nhật', '🇯🇵', 'ja'),
('ka', 'Georgian', 'Tiếng Georgia', '🇬🇪', 'ka'),
('kk', 'Kazakh', 'Tiếng Kazakh', '🇰🇿', 'kk'),
('km', 'Khmer', 'Tiếng Khmer', '🇰🇭', 'km'),
('kn', 'Kannada', 'Tiếng Kannada', '🇮🇳', 'kn'),
('ko', 'Korean', 'Tiếng Hàn', '🇰🇷', 'ko'),
('ky', 'Kyrgyz', 'Tiếng Kyrgyz', '🇰🇬', 'ky'),
('lo', 'Lao', 'Tiếng Lào', '🇱🇦', 'lo'),
('lt', 'Lithuanian', 'Tiếng Lithuania', '🇱🇹', 'lt'),
('lv', 'Latvian', 'Tiếng Latvia', '🇱🇻', 'lv'),
('mk', 'Macedonian', 'Tiếng Macedonia', '🇲🇰', 'mk'),
('ml', 'Malayalam', 'Tiếng Malayalam', '🇮🇳', 'ml'),
('mn', 'Mongolian', 'Tiếng Mông Cổ', '🇲🇳', 'mn'),
('mr', 'Marathi', 'Tiếng Marathi', '🇮🇳', 'mr'),
('ms', 'Malay', 'Tiếng Mã Lai', '🇲🇾', 'ms'),
('my', 'Burmese', 'Tiếng Miến Điện', '🇲🇲', 'my'),
('no', 'Norwegian', 'Tiếng Na Uy', '🇳🇴', 'no'),
('ne', 'Nepali', 'Tiếng Nepal', '🇳🇵', 'ne'),
('nl', 'Dutch', 'Tiếng Hà Lan', '🇳🇱', 'nl'),
('or', 'Odia', 'Tiếng Odia', '🇮🇳', 'or'),
('pa', 'Punjabi', 'Tiếng Punjab', '🇮🇳', 'pa'),
('pl', 'Polish', 'Tiếng Ba Lan', '🇵🇱', 'pl'),
('pt', 'Portuguese', 'Tiếng Bồ Đào Nha', '🇵🇹', 'pt'),
('pt-BR', 'Portuguese (Brazil)', 'Tiếng Bồ Đào Nha (Brazil)', '🇧🇷', 'pt'),
('pt-PT', 'Portuguese (Portugal)', 'Tiếng Bồ Đào Nha (Bồ Đào Nha)', '🇵🇹', 'pt'),
('ro', 'Romanian', 'Tiếng Romania', '🇷🇴', 'ro'),
('ru', 'Russian', 'Tiếng Nga', '🇷🇺', 'ru'),
('si', 'Sinhala', 'Tiếng Sinhala', '🇱🇰', 'si'),
('sk', 'Slovak', 'Tiếng Slovak', '🇸🇰', 'sk'),
('sl', 'Slovenian', 'Tiếng Slovenia', '🇸🇮', 'sl'),
('sq', 'Albanian', 'Tiếng Albania', '🇦🇱', 'sq'),
('sr', 'Serbian', 'Tiếng Serbia', '🇷🇸', 'sr'),
('sr-Latn', 'Serbian (Latin)', 'Tiếng Serbia (Latin)', '🇷🇸', 'sr'),
('sv', 'Swedish', 'Tiếng Thụy Điển', '🇸🇪', 'sv'),
('sw', 'Swahili', 'Tiếng Swahili', '🇰🇪', 'sw'),
('ta', 'Tamil', 'Tiếng Tamil', '🇮🇳', 'ta'),
('te', 'Telugu', 'Tiếng Telugu', '🇮🇳', 'te'),
('th', 'Thai', 'Tiếng Thái', '🇹🇭', 'th'),
('tr', 'Turkish', 'Tiếng Thổ Nhĩ Kỳ', '🇹🇷', 'tr'),
('uk', 'Ukrainian', 'Tiếng Ukraine', '🇺🇦', 'uk'),
('ur', 'Urdu', 'Tiếng Urdu', '🇵🇰', 'ur'),
('uz', 'Uzbek', 'Tiếng Uzbek', '🇺🇿', 'uz'),
('vi', 'Vietnamese', 'Tiếng Việt', '🇻🇳', 'vi'),
('zh-CN', 'Chinese (China)', 'Tiếng Trung (Giản thể)', '🇨🇳', 'zh-CN'),
('zh-HK', 'Chinese (Hong Kong)', 'Tiếng Trung (Hồng Kông)', '🇭🇰', 'zh-TW'),
('zh-TW', 'Chinese (Taiwan)', 'Tiếng Trung (Phồn thể)', '🇹🇼', 'zh-TW'),
('zu', 'Zulu', 'Tiếng Zulu', '🇿🇦', 'zu'),
]

@dataclass
class Language:
    code: str; name_en: str; name_vi: str; flag: str; google_code: str
    @property
    def label(self): return f"{self.flag} {self.name_vi} ({self.name_en}) [{self.code}]"

LANGUAGES = [Language(*r) for r in _RAW]
LANG_BY_CODE = {l.code.lower(): l for l in LANGUAGES}

def normalize_code(c: str) -> str:
    if not c: return ""
    c = c.strip()
    # YouTube sometimes returns 'iw' for Hebrew, 'he' alias
    return c

def base_code(c: str) -> str:
    return (c or "").split("-")[0].lower()

def language_exists(existing_codes, target_code) -> bool:
    """Existing if exact code or same base when target has no region variant handling.
    Exact match wins; also treat 'en' existing covers 'en', base match for zh etc is NOT enough."""
    ex = {e.lower() for e in existing_codes}
    t = target_code.lower()
    if t in ex: return True
    if {t} & {"he", "iw"} and ({"he", "iw"} & ex): return True   # YouTube uses both forms for Hebrew
    # If video already has generic 'es', don't mark es-419/es-US as existing - they are distinct on YouTube
    return False

# ---------- Video ID ----------
_PATTERNS = [
    r"(?:youtube\.com/watch\?[^#]*v=)([A-Za-z0-9_-]{11})",
    r"(?:youtu\.be/)([A-Za-z0-9_-]{11})",
    r"(?:youtube\.com/(?:shorts|live|embed|v)/)([A-Za-z0-9_-]{11})",
    r"(?:music\.youtube\.com/watch\?[^#]*v=)([A-Za-z0-9_-]{11})",
]
def extract_video_id(url: str):
    url = (url or "").strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url): return url
    for p in _PATTERNS:
        m = re.search(p, url)
        if m: return m.group(1)
    return None

def canonical_url(vid: str): return f"https://www.youtube.com/watch?v={vid}"

# ---------- Fetch video info ----------
@dataclass
class VideoInfo:
    video_id: str = ""
    url: str = ""
    title: str = ""
    description: str = ""
    channel: str = ""
    default_language: str = ""
    default_audio_language: str = ""
    existing_languages: list = field(default_factory=list)  # codes from localizations
    existing_details: dict = field(default_factory=dict)    # code -> {title, description}
    source: str = ""   # 'youtube_api' | 'fallback_oembed_scrape' | 'unknown'
    note: str = ""

def fetch_with_youtube_api(video_id, api_key, session=None):
    """Accurate path: needs YouTube Data API v3 key (NOT Gemini/OpenAI key).
    Returns localizations = languages ALREADY added in YouTube Studio."""
    import requests
    s = session
    if s is None:
        s = requests.Session()
    r = s.get("https://www.googleapis.com/youtube/v3/videos",
              params={"part":"snippet,localizations","id":video_id,"key":api_key}, timeout=25)
    if r.status_code != 200:
        raise RuntimeError(f"YouTube API {r.status_code}: {r.text[:300]}")
    items = r.json().get("items", [])
    if not items: raise RuntimeError("Không tìm thấy video (sai ID hoặc video riêng tư/đã xoá)")
    it = items[0]; sn = it.get("snippet", {}); locs = it.get("localizations", {}) or {}
    default_lang = sn.get("defaultLanguage","") or ""
    # snippet localized is the default-localized version
    localized = sn.get("localized", {}) or {}
    details = {}
    for code, v in locs.items():
        details[code] = {"title": v.get("title",""), "description": v.get("description","")}
    title = localized.get("title") or sn.get("title","")
    desc = localized.get("description") or sn.get("description","")
    # If default language localization exists, prefer it as original
    if default_lang and default_lang in details and details[default_lang]["title"]:
        title = details[default_lang]["title"]; desc = details[default_lang]["description"]
    return VideoInfo(video_id=video_id, url=canonical_url(video_id), title=title, description=desc,
                     channel=sn.get("channelTitle",""), default_language=default_lang,
                     default_audio_language=sn.get("defaultAudioLanguage",""),
                     existing_languages=sorted(details.keys()), existing_details=details,
                     source="youtube_api",
                     note="Đã xác minh chính xác qua YouTube Data API v3 (localizations)")

def fetch_fallback(video_id, session=None):
    """No YouTube API key: get original title/desc via oEmbed + watch page meta.
    Existing localizations CANNOT be enumerated publicly without API/OAuth,
    so existing_languages only contains detected original language (if any)."""
    import requests
    s = session or requests.Session()
    headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
               "Accept-Language":"en-US,en;q=0.9"}
    title = ""; desc = ""; channel = ""; detected = ""
    # oEmbed for title/channel (reliable)
    try:
        r = s.get("https://www.youtube.com/oembed", params={"url":canonical_url(video_id),"format":"json"}, timeout=20, headers=headers)
        if r.status_code == 200:
            j = r.json(); title = j.get("title","") or title; channel = j.get("author_name","") or channel
    except Exception:
        pass
    # Watch page for description + ytInitialPlayerResponse
    try:
        r = s.get(canonical_url(video_id), timeout=25, headers=headers)
        if r.status_code == 200:
            txt = r.text
            m = re.search(r"ytInitialPlayerResponse\s*=\s*(\{.+?\});", txt, re.S)
            if m:
                try:
                    data = json.loads(m.group(1))
                    vd = data.get("videoDetails", {}) or {}
                    if vd.get("title"): title = vd["title"]
                    if vd.get("shortDescription"): desc = vd["shortDescription"]
                    if vd.get("author"): channel = vd["author"]
                except Exception: pass
            if not desc:
                m2 = re.search(r'<meta property="og:description" content="([^"]*)"', txt)
                if m2: desc = html.unescape(m2.group(1))
            if not title:
                m3 = re.search(r'<meta property="og:title" content="([^"]*)"', txt)
                if m3: title = html.unescape(m3.group(1))
    except Exception as e:
        pass
    if title:
        detected = detect_language(title) or detected
    existing = []
    if detected: existing = [detected]
    return VideoInfo(video_id=video_id, url=canonical_url(video_id), title=title, description=desc,
                     channel=channel, default_language=detected, existing_languages=existing,
                     source="fallback_oembed_scrape",
                     note="Chưa có YouTube API Key: lấy được tiêu đề/mô tả gốc và ĐÃ nhận diện ngôn ngữ gốc từ chính tiêu đề, nhưng KHÔNG liệt kê được hết ngôn ngữ đã add trong Studio. Hãy nhập YouTube Data API v3 Key ở tab API để xác minh chính xác 100%.")

def fetch_video(video_id_or_url, youtube_api_key=""):
    vid = extract_video_id(video_id_or_url) or video_id_or_url.strip()
    if youtube_api_key.strip():
        return fetch_with_youtube_api(vid, youtube_api_key.strip())
    return fetch_fallback(vid)

def detect_language(text, session=None):
    """Detect the language of a text via Google Translate's public endpoint.
    Returns a language code like 'en'/'vi'/'ja' or '' if detection fails."""
    if not text or not text.strip(): return ""
    try:
        import requests
        s = session or requests.Session()
        r = s.get("https://translate.googleapis.com/translate_a/single",
                  params={"client":"gtx","sl":"auto","tl":"en","dt":"t","q":text[:400]}, timeout=15)
        if r.status_code != 200: return ""
        data = r.json()
        if isinstance(data, list) and len(data) > 2 and isinstance(data[2], str):
            return data[2]
    except Exception:
        pass
    return ""

# ---------- Translation engines ----------
def _chunks(text, limit=3500):
    if len(text) <= limit: return [text]
    parts, cur = [], ""
    for para in text.split("\n"):
        if len(cur) + len(para) + 1 > limit and cur:
            parts.append(cur); cur = para
        else:
            cur = (cur + "\n" + para) if cur else para
    if cur: parts.append(cur)
    return parts

import threading
_GTX_LOCK = threading.Lock(); _GTX_LAST = [0.0]
def _gtx_throttle(min_gap=0.34):
    """Global pacing for the free Google endpoint (~4.5 req/s max) so parallel
    workers do not trip its rate limit (HTTP 429)."""
    with _GTX_LOCK:
        now = time.monotonic(); wait = min_gap - (now - _GTX_LAST[0])
        if wait > 0: time.sleep(wait)
        _GTX_LAST[0] = time.monotonic()

GTX_HOSTS = ("translate.google.com.vn", "translate.googleapis.com")

class GtxBlockedError(RuntimeError):
    """Google is refusing EVERY request from this IP (429 at all doors)."""

_GTX_FAILS = [0]
def _is_429(e): 
    s = str(e).lower()
    return "429" in s or "too many" in s
def _note_gtx(ok):
    with _GTX_LOCK:
        _GTX_FAILS[0] = 0 if ok else _GTX_FAILS[0] + 1

GTX_BLOCKED_MSG = ("Google đang CHẶN IP của bạn (mọi cửa dịch đều trả 429 liên tục) — "
    "thử tiếp chỉ làm thời gian chặn lâu hơn. Cách xử lý: 1) DỪNG hẳn 30–60 phút rồi chạy lại, "
    "2) đổi mạng (bật hotspot 4G từ điện thoại = IP mới, dịch được ngay), "
    "3) hoặc nhập Gemini key ở tab 8 — có key là tool TỰ chuyển sang Gemini dịch thay khi Google bị chặn (flash-lite ~500 lượt/ngày).")

def _google_gtx_chunk(ch, target: Language, source_code="auto", host="translate.google.com.vn"):
    """Raw gtx endpoint on a Google Translate host (the .vn door first, per user choice)."""
    import requests
    src = "auto" if not source_code or source_code == "auto" else base_code(source_code)
    r = requests.get(f"https://{host}/translate_a/single",
                     params={"client": "gtx", "sl": src, "tl": target.google_code, "dt": "t", "q": ch},
                     timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    data = r.json()
    return "".join(seg[0] for seg in data[0] if seg and seg[0])

def _google_one_chunk(ch, target: Language, source_code="auto"):
    """Door order: 1) translate.google.com.vn (fast for VN users), 2) deep-translator
    (translate.google.com), 3) translate.googleapis.com. First door that answers wins."""
    try:
        out = _google_one_chunk_doors(ch, target, source_code)
    except Exception as e:
        if _is_429(e): _note_gtx(False)
        raise
    _note_gtx(True)
    return out

def _google_one_chunk_doors(ch, target: Language, source_code="auto"):
    _gtx_throttle()
    try:
        return _google_gtx_chunk(ch, target, source_code, GTX_HOSTS[0])
    except Exception:
        pass
    try:
        from deep_translator import GoogleTranslator
        src = "auto" if not source_code or source_code=="auto" else base_code(source_code)
        return GoogleTranslator(source=src, target=target.google_code).translate(ch)
    except ImportError:
        return _google_gtx_chunk(ch, target, source_code, GTX_HOSTS[1])
    except Exception as e:
        if "429" in str(e) or "too many" in str(e).lower():
            _gtx_throttle()
            return _google_gtx_chunk(ch, target, source_code, GTX_HOSTS[1])
        raise

def translate_google(text, target: Language, source_code="auto"):
    """Free, no key. Auto-retries with backoff when Google rate-limits (HTTP 429):
    waits 8s, then 20s before giving up on that chunk. A global circuit breaker
    stops the whole run early when Google is blocking this IP outright."""
    if not text or not text.strip(): return text
    outs = []
    for ch in _chunks(text, 4500):
        if _GTX_FAILS[0] >= 3: raise GtxBlockedError(GTX_BLOCKED_MSG)   # earlier chunks already proved the block
        last_err = None
        for wait in (0, 8, 20):
            if wait:
                if _GTX_FAILS[0] >= 3: break
                time.sleep(wait)
            try:
                outs.append(_google_one_chunk(ch, target, source_code)); last_err = None; break
            except Exception as e:
                last_err = e
                if not _is_429(e):
                    raise
        if last_err is not None and _is_429(last_err) and _GTX_FAILS[0] >= 3:
            time.sleep(30)   # one real cooldown, then a single final probe
            try:
                outs.append(_google_one_chunk(ch, target, source_code)); last_err = None
            except Exception as e2:
                if _is_429(e2): raise GtxBlockedError(GTX_BLOCKED_MSG)
                raise
        if last_err is not None:
            raise RuntimeError(f"Google dịch miễn phí giới hạn tốc độ (429) kéo dài — hãy chờ vài phút, giảm số ngôn ngữ mỗi đợt, hoặc dùng Gemini/OpenAI key. Chi tiết: {last_err}")
        time.sleep(0.35)
    return "\n".join(outs) if len(_chunks(text,4500))>1 else outs[0]

_AI_RULES = """You are a professional YouTube localization translator.
Translate the text into {lang} ({code}) naturally, like a native YouTube creator.
RULES: Keep ALL URLs, hashtags (#...), @mentions, emojis, line breaks, numbers and timestamps EXACTLY unchanged.
Do NOT add explanations. Do NOT wrap in quotes/code blocks. Output ONLY the translation."""

GEMINI_FALLBACKS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.8-pro"]
GEMINI_RETIRED = {"gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash",
                  "gemini-1.5-flash-8b", "gemini-1.5-pro", "gemini-pro", "gemini-1.0-pro",
                  "gemini-2.5-pro", "gemini-2.5-flash"}
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"

def _gemini_chain(model):
    chain = []
    if model and model not in GEMINI_RETIRED: chain.append(model)
    if DEFAULT_GEMINI_MODEL not in chain: chain.append(DEFAULT_GEMINI_MODEL)
    for f in GEMINI_FALLBACKS:
        if f not in chain: chain.append(f)
    return chain

def translate_gemini(text, target: Language, api_key, model=DEFAULT_GEMINI_MODEL):
    """Gemini translation with a model fallback chain: retired models (404) and
    transient 503/timeouts move on to the next model instead of failing the language."""
    import requests
    if not text or not text.strip(): return text
    outs=[]
    for ch in _chunks(text, 6000):
        prompt = _AI_RULES.format(lang=target.name_en, code=target.code) + "\n\nTEXT:\n" + ch
        errors = []
        for m in _gemini_chain(model):
            ok = False
            for attempt, wait in enumerate((0, 6)):
                if wait: time.sleep(wait)
                try:
                    r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent",
                                      params={"key": api_key}, json={"contents": [{"parts": [{"text": prompt}]}]}, timeout=90)
                except Exception as e:
                    errors.append(f"{m}: {type(e).__name__}"); continue
                if r.status_code == 200:
                    try: outs.append(r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()); ok = True
                    except Exception: errors.append(f"{m}: trả về lạ")
                    break
                errors.append(f"{m}: HTTP {r.status_code}")
                if r.status_code == 404: break
                if r.status_code not in (429, 500, 502, 503, 504): break
            if ok: break
        else:
            raise RuntimeError("Gemini lỗi ở mọi model — " + " | ".join(errors[-4:]))
    return "\n".join(outs)

def translate_openai(text, target: Language, api_key, model="gpt-4o-mini", base_url="https://api.openai.com/v1"):
    import requests
    if not text or not text.strip(): return text
    outs=[]
    for ch in _chunks(text, 6000):
        r = requests.post(base_url.rstrip("/")+"/chat/completions",
            headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},
            json={"model":model,"temperature":0.3,
                  "messages":[{"role":"system","content":_AI_RULES.format(lang=target.name_en, code=target.code)},
                              {"role":"user","content":ch}]}, timeout=60)
        if r.status_code!=200: raise RuntimeError(f"OpenAI {r.status_code}: {r.text[:300]}")
        outs.append(r.json()["choices"][0]["message"]["content"].strip())
    return "\n".join(outs)

# ---------- Force the CORRECT target language on free Google Translate ----------
_SCRIPT_RANGES = {
 "am": [(0x1200,0x137F)], "hy": [(0x0530,0x058F)], "ka": [(0x10A0,0x10FF)],
 "he": [(0x0590,0x05FF)], "yi": [(0x0590,0x05FF)],
 "ar": [(0x0600,0x06FF),(0x0750,0x077F)], "fa": [(0x0600,0x06FF)], "ur": [(0x0600,0x06FF)],
 "ps": [(0x0600,0x06FF)], "sd": [(0x0600,0x06FF)], "ug": [(0x0600,0x06FF)],
 "el": [(0x0370,0x03FF)],
 "ru": [(0x0400,0x04FF)], "uk": [(0x0400,0x04FF)], "bg": [(0x0400,0x04FF)], "sr": [(0x0400,0x04FF)],
 "mk": [(0x0400,0x04FF)], "be": [(0x0400,0x04FF)], "kk": [(0x0400,0x04FF)], "ky": [(0x0400,0x04FF)],
 "mn": [(0x0400,0x04FF)], "tg": [(0x0400,0x04FF)],
 "zh": [(0x4E00,0x9FFF)], "ja": [(0x3040,0x30FF),(0x4E00,0x9FFF)], "ko": [(0xAC00,0xD7AF),(0x1100,0x11FF)],
 "th": [(0x0E00,0x0E7F)], "lo": [(0x0E80,0x0EFF)], "km": [(0x1780,0x17FF)], "my": [(0x1000,0x109F)],
 "hi": [(0x0900,0x097F)], "mr": [(0x0900,0x097F)], "ne": [(0x0900,0x097F)],
 "bn": [(0x0980,0x09FF)], "as": [(0x0980,0x09FF)], "pa": [(0x0A00,0x0A7F)], "gu": [(0x0A80,0x0AFF)],
 "or": [(0x0B00,0x0B7F)], "ta": [(0x0B80,0x0BFF)], "te": [(0x0C00,0x0C7F)], "kn": [(0x0C80,0x0CFF)],
 "ml": [(0x0D00,0x0D7F)], "si": [(0x0D80,0x0DFF)],
}
_SCRIPT_SOFT = {"sr"}   # dual-script languages: script mismatch alone is not fatal
_LANG_ALIAS = {"iw": "he", "zh-cn": "zh", "zh-tw": "zh", "zh-hk": "zh", "pt-br": "pt",
               "pt-pt": "pt", "fil": "tl", "nb": "no", "nn": "no", "in": "id", "jw": "jv"}
_COUSINS = {frozenset(p) for p in [("ca","es"),("id","ms"),("sr","hr"),("sr","bs"),("hr","bs"),
                                   ("uk","ru"),("nb","da"),("nn","da"),("gl","pt"),("gl","es")]}

def _norm_lang(code):
    code = (code or "").lower().replace("_", "-")
    return _LANG_ALIAS.get(code, code.split("-")[0])

def detect_language_gtx(text):
    """Ask the free Google endpoint which language a text is in. '' when unknown."""
    if not text or not text.strip(): return ""
    import requests
    for host in GTX_HOSTS:
        try:
            _gtx_throttle()
            r = requests.get(f"https://{host}/translate_a/single",
                             params={"client": "gtx", "sl": "auto", "tl": "en", "dt": "t", "q": text[:800]},
                             timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status(); data = r.json()
            if isinstance(data, list) and len(data) > 2 and data[2]: return str(data[2]).lower()
        except Exception: continue
    return ""

def _verify_language(sample, lang):
    """(verdict, detected): ok | cousin | bad | skip — is `sample` really in lang?"""
    if not sample or len(sample.strip()) < 25: return ("skip", "")
    code = base_code(lang.code).lower()
    rng = _SCRIPT_RANGES.get(_norm_lang(code)) or _SCRIPT_RANGES.get(code)
    if rng:
        letters = [ch for ch in sample if ch.isalpha()]
        if len(letters) >= 20:
            hit = sum(1 for ch in letters if any(a <= ord(ch) <= b for a, b in rng))
            ratio = hit / len(letters)
            if ratio < 0.25 and code not in _SCRIPT_SOFT:
                return ("bad", "khác hệ chữ")
            if ratio >= 0.5:
                return ("ok", "đúng hệ chữ")   # strong script match: no detect request needed
    det = detect_language_gtx(sample)
    if not det: return ("skip", "")
    nd, ne = _norm_lang(det), _norm_lang(lang.google_code)
    if nd == ne: return ("ok", det)
    if frozenset((nd, ne)) in _COUSINS: return ("cousin", det)
    return ("bad", det)


def _ai_pair(title, desc, lang, cfg, source_code="auto", do_title=True, do_desc=True, log=lambda m: None):
    """Rescue translation via AI engines when free Google fails: Gemini first,
    then OpenAI — whichever key the user has configured."""
    errs = []
    for eng, keyname in (("gemini", "gemini_key"), ("openai", "openai_key")):
        if not (cfg or {}).get(keyname): continue
        try:
            t = translate_text(title, lang, eng, cfg, source_code) if do_title else ""
            d = translate_text(desc, lang, eng, cfg, source_code) if do_desc else ""
            return t, d
        except Exception as e:
            errs.append(f"{eng}: {str(e)[:110]}")
    raise RuntimeError("Google lỗi và AI cũng không dịch thay được — " + (" · ".join(errs) or "chưa nhập Gemini/OpenAI key ở tab 8"))

def translate_pair(title, desc, lang, engine, cfg, source_code="auto",
                   do_title=True, do_desc=True, log=lambda m: None):
    """Translate title+description into ONE language. For the free Google engine the
    result is VERIFIED to really be in the target language: wrong-language output is
    retried once with a hard-forced source language, then reported as an error
    instead of silently saving a wrong-language translation."""
    eng = (engine or "google").lower()
    if eng != "google":
        t = translate_text(title, lang, eng, cfg, source_code) if do_title else ""
        d = translate_text(desc, lang, eng, cfg, source_code) if do_desc else ""
        return t, d
    has_ai = bool((cfg or {}).get("gemini_key") or (cfg or {}).get("openai_key"))
    if has_ai and _GTX_FAILS[0] >= 3:
        log(f"🔁 {lang.flag} {lang.code}: Google đang bị chặn IP — Gemini/OpenAI dịch thay")
        return _ai_pair(title, desc, lang, cfg, source_code, do_title, do_desc, log)
    try:
        src = source_code if source_code and source_code != "auto" else "auto"
        t = translate_google(title, lang, src) if do_title else ""
        d = translate_google(desc, lang, src) if do_desc else ""
        sample = d if len(d or "") >= 25 else ((t or "") + " " + (d or ""))
        verdict, det = _verify_language(sample, lang)
        if verdict == "cousin":
            log(f"⚠️ {lang.flag} {lang.code}: dò ra '{det}' (ngôn ngữ họ hàng gần, khó phân biệt) — chấp nhận")
        if verdict != "bad": return t, d
        forced = src
        if forced == "auto":
            forced = detect_language_gtx((title or "") + " " + (desc or "")) or "en"
        log(f"↻ {lang.flag} {lang.code}: Google trả SAI ngôn ngữ ({det}) — dịch lại với nguồn ép cứng '{forced}'")
        t = translate_google(title, lang, forced) if do_title else ""
        d = translate_google(desc, lang, forced) if do_desc else ""
        sample = d if len(d or "") >= 25 else ((t or "") + " " + (d or ""))
        verdict2, det2 = _verify_language(sample, lang)
        if verdict2 == "bad":
            raise RuntimeError(f"Google vẫn dịch sai ngôn ngữ cho {lang.name_vi} [{lang.code}] (dò ra '{det2}') — bỏ qua để tránh đăng sai")
        return t, d
    except Exception as e:
        if not has_ai: raise
        log(f"🔁 {lang.flag} {lang.code}: Google dịch lỗi ({str(e)[:90]}) — chuyển Gemini/OpenAI dịch thay")
        return _ai_pair(title, desc, lang, cfg, source_code, do_title, do_desc, log)

def translate_many(title, desc, targets, engine, cfg, source_code="auto",
                   log=lambda m: None, progress=None, is_cancelled=None,
                   do_title=True, do_desc=True):
    """Translate title+description into many languages IN PARALLEL.
    AI engines (Gemini/OpenAI) run 8 at a time; free Google runs 3 (it rate-limits).
    Returns {lang_code: result}. progress(done, total, label) is called as each finishes."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    _GTX_FAILS[0] = 0
    workers = 4 if (engine or "google").lower() in ("gemini", "openai", "chatgpt", "gpt") else 2
    results = {}
    blocked = [0]
    def job(lang):
        if blocked[0] >= 3: return None
        if is_cancelled and is_cancelled(): return None
        t, d = translate_pair(title, desc, lang, engine, cfg, source_code, do_title, do_desc, log=log)
        return lang, {"title": t, "description": d, "lang": lang, "status": "ok"}
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(job, l): l for l in targets}
        for f in as_completed(futs):
            lang = futs[f]
            try:
                r = f.result()
                if r:
                    results[r[0].code] = r[1]
                    log(f"✅ {lang.flag} {lang.name_vi} [{lang.code}] xong")
            except Exception as e:
                if isinstance(e, GtxBlockedError):
                    blocked[0] += 1
                    if blocked[0] == 1: log(f"⛔ {str(e)}")
                    if blocked[0] >= 3: log("🛑 Đã dừng đợt dịch — Google đang chặn IP, dịch tiếp cũng thất bại.")
                else:
                    log(f"❌ {lang.flag} {lang.code}: {str(e)[:160]}")
            done += 1
            if progress: progress(done, len(targets), f"{lang.flag} {lang.name_vi}")
    return results

def translate_text(text, target: Language, engine, cfg: dict, source_code="auto"):
    engine = (engine or "google").lower()
    if engine=="gemini":
        key=cfg.get("gemini_key","").strip()
        if not key: raise RuntimeError("Chưa nhập Gemini API Key")
        return translate_gemini(text, target, key, cfg.get("gemini_model", DEFAULT_GEMINI_MODEL) or DEFAULT_GEMINI_MODEL)
    if engine in ("openai","chatgpt","gpt"):
        key=cfg.get("openai_key","").strip()
        if not key: raise RuntimeError("Chưa nhập OpenAI / ChatGPT API Key")
        return translate_openai(text, target, key, cfg.get("openai_model","gpt-4o-mini") or "gpt-4o-mini")
    return translate_google(text, target, source_code)

# ---------- Export TXT ----------
def safe_name(s, maxlen=60):
    s = re.sub(r'[\\/:*?"<>|]+', "_", (s or "").strip())
    s = re.sub(r"\s+", " ", s)
    return (s[:maxlen].strip() or "video")

def export_video_results(video: VideoInfo, results: dict, out_dir, combined=True, src_title=None, src_desc=None):
    """results: {code: {'title':..,'description':..,'lang':Language,'status':..}}
    Creates: <out>/<video_id>_<title>/  01_[flag]_[code]_Name.txt + ALL_LANGUAGES.txt
    src_title/src_desc: working (possibly AI-rewritten) source texts actually translated,
    when they differ from the video's current YouTube title/description.
    Returns list of written file paths."""
    import os
    folder = os.path.join(out_dir, f"{video.video_id}_{safe_name(src_title or video.title, 40)}")
    os.makedirs(folder, exist_ok=True)
    written=[]
    all_lines=[]
    header = [f"{APP_NAME} v{VERSION}", f"Bản quyền: {COPYRIGHT}",
              f"Video: {src_title or video.title}", f"Link: {video.url}", f"ID: {video.video_id}",
              f"Kênh: {video.channel}", f"Ngôn ngữ gốc (defaultLanguage): {video.default_language or 'không rõ'}",
              f"Ngôn ngữ ĐÃ CÓ trên YouTube: {', '.join(video.existing_languages) if video.existing_languages else '(chưa xác minh được / chưa có)'}",
              "="*72, ""]
    all_lines.extend(header)
    for idx, code in enumerate(sorted(results.keys()), 1):
        r = results[code]; lang: Language = r["lang"]
        block = [f"{lang.flag} [{code}] {lang.name_vi} — {lang.name_en}",
                 "-"*72,
                 "TIÊU ĐỀ / TITLE:",
                 r.get("title",""), "",
                 "MÔ TẢ / DESCRIPTION:",
                 r.get("description",""), "", "="*72, ""]
        fname = f"{idx:02d}_{code}_{safe_name(lang.name_en,30)}.txt"
        path = os.path.join(folder, fname)
        with open(path,"w",encoding="utf-8") as f:
            f.write("\n".join(header + block))
        written.append(path)
        all_lines.extend(block)
    if combined:
        p = os.path.join(folder, "ALL_LANGUAGES.txt")
        with open(p,"w",encoding="utf-8") as f: f.write("\n".join(all_lines))
        written.insert(0,p)
        # JSON for re-import / automation
        pj = os.path.join(folder, "translations.json")
        with open(pj,"w",encoding="utf-8") as f:
            json.dump({"video":asdict(video),
                       "results":{k:{"title":v.get("title",""),"description":v.get("description",""),
                                     "language":v["lang"].code,"flag":v["lang"].flag,
                                     "name_vi":v["lang"].name_vi,"name_en":v["lang"].name_en} for k,v in results.items()}},
                      f, ensure_ascii=False, indent=2)
        written.append(pj)
    return written

# ---------- Auto-push to channel: OAuth 2.0 + YouTube Data API v3 videos.update ----------
# NOTE: An API Key alone CANNOT write to a channel. Writing requires OAuth 2.0:
# the channel owner signs in with Google and grants this app the youtube.force-ssl scope.
# The user supplies THEIR OWN OAuth Desktop Client (ID + Secret) from Google Cloud Console.
import os, threading, webbrowser, subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

YT_SCOPE = "https://www.googleapis.com/auth/youtube.force-ssl"
OAUTH_TOKEN_PATH = os.path.join(os.path.expanduser("~"), ".yt_lang_translator_oauth.json")

def build_localizations(video: VideoInfo, results: dict, full_snippet=None, full_localizations=None):
    """Merge: existing localizations on YouTube are KEPT, new translations are added/overwrite
    only their own language code. Returns dict for videos.update body."""
    merged = {}
    for code, v in (full_localizations or {}).items():
        merged[code] = {"title": v.get("title",""), "description": v.get("description","")}
    for code, r in (results or {}).items():
        title = (r.get("title") or "").strip()
        desc = r.get("description") or ""
        if not title:
            title = merged.get(code, {}).get("title") or video.title
        if not desc:
            desc = merged.get(code, {}).get("description") or video.description
        merged[code] = {"title": title, "description": desc}
    return merged

def build_update_body(video: VideoInfo, results: dict, full_snippet: dict):
    """full_snippet MUST come from a fresh videos.list call so categoryId/tags/defaultLanguage
    of the original video are preserved exactly (YouTube rejects update without categoryId)."""
    sn = full_snippet or {}
    snippet = {
        "title": sn.get("title") or video.title,
        "description": sn.get("description") if sn.get("description") is not None else video.description,
        "categoryId": sn.get("categoryId") or "22",
    }
    if sn.get("tags"): snippet["tags"] = sn["tags"]
    if sn.get("defaultLanguage"): snippet["defaultLanguage"] = sn["defaultLanguage"]
    if sn.get("defaultAudioLanguage"): snippet["defaultAudioLanguage"] = sn["defaultAudioLanguage"]
    return {"id": video.video_id, "snippet": snippet,
            "localizations": build_localizations(video, results, full_snippet, None)}


# ---------- choose which browser opens the OAuth login page ----------
_BROWSER_PATHS = {
    "coccoc": [os.path.join(os.environ.get("LOCALAPPDATA", ""), "CocCoc", "Browser", "Application", "browser.exe"),
               os.path.join(os.environ.get("ProgramFiles", ""), "CocCoc", "Browser", "Application", "browser.exe"),
               os.path.join(os.environ.get("ProgramFiles(x86)", ""), "CocCoc", "Browser", "Application", "browser.exe")],
    "chrome": [os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
               os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
               os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe")],
    "edge": [os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
             os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe")],
}
_BROWSER_NAMES = {"coccoc": "Cốc Cốc", "chrome": "Google Chrome", "edge": "Microsoft Edge"}


def _browser_from_registry(choice):
    """Fallback: ask Windows' StartMenuInternet registry where the browser lives
    (covers non-standard install locations, e.g. CocCoc installed system-wide)."""
    try:
        import winreg
    except Exception:
        return None
    needles = {"coccoc": ("coccoc", "cốc cốc"), "chrome": ("google chrome",), "edge": ("microsoft edge",)}
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, r"SOFTWARE\Clients\StartMenuInternet") as k:
                n = winreg.QueryInfoKey(k)[0]
                for i in range(n):
                    name = winreg.EnumKey(k, i)
                    if any(t in name.lower() for t in needles.get(choice, ())):
                        try:
                            with winreg.OpenKey(k, name + r"\shell\open\command") as ck:
                                cmd, _ = winreg.QueryValueEx(ck, None)
                            exe = cmd.strip().strip('"').split('"')[0]
                            if exe and os.path.exists(exe): return exe
                        except Exception:
                            pass
        except Exception:
            pass
    return None

def open_auth_url(url, choice="default", log=lambda m: None):
    """Open the OAuth URL in the browser the user picked — their channel account
    may be signed in on CocCoc while the OS default browser is another one.
    The redirect target is 127.0.0.1, so ANY browser works."""
    if choice in _BROWSER_PATHS:
        for p in _BROWSER_PATHS[choice]:
            if p and os.path.exists(p):
                try:
                    subprocess.Popen([p, url]); log(f"🌐 Đã mở trang đăng nhập bằng {_BROWSER_NAMES[choice]}"); return True
                except Exception:
                    pass
        reg = _browser_from_registry(choice)
        if reg:
            try:
                subprocess.Popen([reg, url]); log(f"🌐 Đã mở trang đăng nhập bằng {_BROWSER_NAMES[choice]}"); return True
            except Exception:
                pass
        log(f"⚠️ Không tìm thấy {_BROWSER_NAMES[choice]} trên máy — mở bằng trình duyệt mặc định")
    webbrowser.open(url); return False

class YouTubeUploader:
    def __init__(self, client_id, client_secret, token_path=OAUTH_TOKEN_PATH, session=None):
        import requests
        self.client_id = (client_id or "").strip()
        self.client_secret = (client_secret or "").strip()
        self.token_path = token_path
        self.s = session or requests.Session()
        self.token = {}
        if os.path.exists(token_path):
            try: self.token = json.load(open(token_path, encoding="utf-8"))
            except Exception: self.token = {}
        self._access = self.token.get("access_token", "")
        self._exp = float(self.token.get("expires_at", 0) or 0)
        self.on_quota = None  # optional callable(units:int) — GUI hooks this to show daily quota

    def _spend(self, units):
        if self.on_quota:
            try: self.on_quota(units)
            except Exception: pass

    # --- OAuth flow (desktop: local redirect server) ---
    def auth_url(self, redirect_uri):
        q = urllib.parse.urlencode({
            "client_id": self.client_id, "redirect_uri": redirect_uri,
            "response_type": "code", "scope": YT_SCOPE,
            "access_type": "offline", "prompt": "consent"})
        return "https://accounts.google.com/o/oauth2/v2/auth?" + q

    def login_interactive(self, log=lambda m: None, timeout_sec=240, browser="default", on_url=None):
        """Opens browser, waits for Google redirect on a local port, exchanges the code.
        Returns the granted token dict. Raises on timeout/denial."""
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Chưa nhập OAuth Client ID / Client Secret (tab Đẩy lên kênh có hướng dẫn tạo)")
        holder = {}
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if "code" in qs: holder["code"] = qs["code"][0]
                if "error" in qs: holder["error"] = qs["error"][0]
                self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.end_headers()
                self.wfile.write("Đăng nhập thành công! Bạn có thể đóng tab này và quay lại tool.".encode("utf-8"))
            def log_message(self, *a): pass
        srv = HTTPServer(("127.0.0.1", 0), H)
        port = srv.server_address[1]
        redirect_uri = f"http://127.0.0.1:{port}/"
        t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
        url = self.auth_url(redirect_uri)
        if on_url:
            try: on_url(url)
            except Exception: pass
        open_auth_url(url, browser, log)
        waited = 0
        try:
            while "code" not in holder and "error" not in holder and waited < timeout_sec:
                time.sleep(0.5); waited += 0.5
        finally:
            srv.shutdown()
        if "error" in holder: raise RuntimeError(f"Google từ chối đăng nhập: {holder['error']}")
        if "code" not in holder: raise RuntimeError("Hết thời gian chờ đăng nhập Google (bạn chưa hoàn tất ở trình duyệt)")
        r = self.s.post("https://oauth2.googleapis.com/token", data={
            "code": holder["code"], "client_id": self.client_id, "client_secret": self.client_secret,
            "redirect_uri": redirect_uri, "grant_type": "authorization_code"}, timeout=30)
        if r.status_code != 200: raise RuntimeError(f"Đổi code lấy token lỗi {r.status_code}: {r.text[:250]}")
        tok = r.json()
        self.token = {"refresh_token": tok.get("refresh_token", self.token.get("refresh_token","")),
                      "access_token": tok.get("access_token",""),
                      "expires_at": time.time() + int(tok.get("expires_in", 3600)) - 60}
        self._save(); return self.token

    # --- OAuth flow (iOS: fixed loopback port + manual paste-code fallback) ---
    IOS_REDIRECT = "http://127.0.0.1:8765/"

    def exchange_code(self, code, redirect_uri=None):
        redirect_uri = redirect_uri or self.IOS_REDIRECT
        r = self.s.post("https://oauth2.googleapis.com/token", data={
            "code": (code or "").strip(), "client_id": self.client_id, "client_secret": self.client_secret,
            "redirect_uri": redirect_uri, "grant_type": "authorization_code"}, timeout=30)
        if r.status_code != 200: raise RuntimeError(f"Đổi code lấy token lỗi {r.status_code}: {r.text[:250]}")
        tok = r.json()
        self.token = {"refresh_token": tok.get("refresh_token", self.token.get("refresh_token", "")),
                      "access_token": tok.get("access_token", ""),
                      "expires_at": time.time() + int(tok.get("expires_in", 3600)) - 60}
        self._save(); return self.token

    def login_ios(self, log=lambda m: None, on_url=None, timeout_sec=300):
        """iOS login: Safari opens the consent page; the loopback server on the
        fixed port catches the redirect while the app is backgrounded. If iOS
        suspends the app first, the user can paste the redirect link/code and
        the UI calls exchange_code() with IOS_REDIRECT instead."""
        if not self.client_id or not self.client_secret:
            raise RuntimeError("Chưa nhập OAuth Client ID / Client Secret (màn hình Kênh & API)")
        holder = {}
        class H(BaseHTTPRequestHandler):
            def do_GET(self):
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                if "code" in qs: holder["code"] = qs["code"][0]
                if "error" in qs: holder["error"] = qs["error"][0]
                self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers()
                self.wfile.write("Đăng nhập thành công! Quay lại app YT Studio Pro.".encode("utf-8"))
            def log_message(self, *a): pass
        srv = HTTPServer(("127.0.0.1", 8765), H)
        t = threading.Thread(target=srv.serve_forever, daemon=True); t.start()
        url = self.auth_url(self.IOS_REDIRECT)
        if on_url:
            try: on_url(url)
            except Exception: pass
        waited = 0
        try:
            while "code" not in holder and "error" not in holder and waited < timeout_sec:
                if self.token.get("refresh_token"): return self.token   # pasted-code path won
                time.sleep(0.5); waited += 0.5
        finally:
            try: srv.shutdown()
            except Exception: pass
        if "error" in holder: raise RuntimeError(f"Google từ chối đăng nhập: {holder['error']}")
        if "code" not in holder: raise RuntimeError("Hết thời gian chờ đăng nhập — hãy dùng ô dán code/link bên dưới")
        return self.exchange_code(holder["code"], self.IOS_REDIRECT)

    def _save(self):
        with open(self.token_path, "w", encoding="utf-8") as f:
            json.dump(self.token, f, ensure_ascii=False, indent=2)

    def logout(self):
        self.token = {}; self._access = ""
        try: os.remove(self.token_path)
        except Exception: pass

    @property
    def logged_in(self): return bool(self.token.get("refresh_token"))

    def access_token(self):
        if self._access and time.time() < self._exp: return self._access
        rt = self.token.get("refresh_token")
        if not rt: raise RuntimeError("Chưa đăng nhập Google — hãy bấm 'Đăng nhập Google' trước")
        r = self.s.post("https://oauth2.googleapis.com/token", data={
            "refresh_token": rt, "client_id": self.client_id, "client_secret": self.client_secret,
            "grant_type": "refresh_token"}, timeout=30)
        if r.status_code != 200: raise RuntimeError(f"Làm mới token lỗi {r.status_code}: {r.text[:250]}")
        tok = r.json()
        self.token["access_token"] = tok["access_token"]
        self.token["expires_at"] = time.time() + int(tok.get("expires_in", 3600)) - 60
        self._access = self.token["access_token"]; self._exp = self.token["expires_at"]
        self._save(); return self._access

    def _auth_headers(self): return {"Authorization": f"Bearer {self.access_token()}", "Content-Type": "application/json"}

    def channel_info(self):
        r = self.s.get("https://www.googleapis.com/youtube/v3/channels",
                       params={"part": "snippet", "mine": "true"}, headers=self._auth_headers(), timeout=25)
        if r.status_code != 200: raise RuntimeError(f"Lấy kênh lỗi {r.status_code}: {r.text[:250]}")
        items = r.json().get("items", [])
        if not items: raise RuntimeError("Google báo danh tính này chưa có kênh YouTube. Nếu kênh của bạn là KÊNH THƯƠNG HIỆU (Brand Account): "
                            "lúc đăng nhập Google có một bước CHỌN KÊNH — hãy chọn đúng TÊN KÊNH THƯƠNG HIỆU thay vì tài khoản cá nhân. "
                            "Nếu không thấy bước chọn kênh: bấm Đăng xuất trong tool, vào myaccount.google.com/permissions xoá quyền của app này, rồi đăng nhập lại.")
        return items[0]["snippet"].get("title", ""), items[0].get("id", "")

    def fetch_full(self, video_id):
        r = self.s.get("https://www.googleapis.com/youtube/v3/videos",
                       params={"part": "snippet,localizations", "id": video_id},
                       headers=self._auth_headers(), timeout=25)
        if r.status_code != 200: raise RuntimeError(f"videos.list lỗi {r.status_code}: {r.text[:250]}")
        items = r.json().get("items", [])
        if not items: raise RuntimeError(f"Không thấy video {video_id}")
        return items[0].get("snippet", {}) or {}, items[0].get("localizations", {}) or {}

    def push_video(self, video: VideoInfo, results: dict, backup_dir=None, log=lambda m: None):
        """ONE videos.update call per video pushes ALL new languages at once (50 quota units).
        Existing localizations are merged back in, so nothing already on the channel is lost.
        Returns (pushed_codes, backup_path_or_None)."""
        snippet, existing = self.fetch_full(video.video_id)
        backup_path = None
        if backup_dir:
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f"backup_localizations_{video.video_id}.json")
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump({"snippet": snippet, "localizations": existing}, f, ensure_ascii=False, indent=2)
            log(f"🛟 Đã sao lưu bản dịch cũ của {video.video_id} → {backup_path}")
        body = build_update_body(video, results, snippet)
        body["localizations"] = build_localizations(video, results, snippet, existing)
        r = self.s.put("https://www.googleapis.com/youtube/v3/videos",
                       params={"part": "snippet,localizations"},
                       headers=self._auth_headers(), data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                       timeout=40)
        self._spend(50)
        if r.status_code != 200:
            raise RuntimeError(f"videos.update lỗi {r.status_code}: {r.text[:400]}")
        return sorted(results.keys()), backup_path

    # ---------- Studio API (channel, competitors, stats, snippet, captions, comments) ----------
    def _api_get(self, path, params, cost=1):
        r = self.s.get(f"https://www.googleapis.com/youtube/v3/{path}", params=params,
                       headers=self._auth_headers(), timeout=30)
        self._spend(cost)
        if r.status_code != 200:
            raise RuntimeError(f"{path} lỗi {r.status_code}: {r.text[:300]}")
        return r.json()

    def my_channel(self):
        d = self._api_get("channels", {"part": "snippet,contentDetails", "mine": "true"})
        items = d.get("items", [])
        if not items: raise RuntimeError("Google báo danh tính này chưa có kênh YouTube. Nếu kênh của bạn là KÊNH THƯƠNG HIỆU (Brand Account): "
                            "lúc đăng nhập Google có một bước CHỌN KÊNH — hãy chọn đúng TÊN KÊNH THƯƠNG HIỆU thay vì tài khoản cá nhân. "
                            "Nếu không thấy bước chọn kênh: bấm Đăng xuất trong tool, vào myaccount.google.com/permissions xoá quyền của app này, rồi đăng nhập lại.")
        it = items[0]
        return {"id": it["id"], "title": it["snippet"].get("title", ""),
                "uploads": it["contentDetails"]["relatedPlaylists"]["uploads"]}

    def playlist_video_ids(self, playlist_id, max_results=20):
        ids, token = [], None
        while len(ids) < max_results:
            p = {"part": "contentDetails", "playlistId": playlist_id, "maxResults": min(50, max_results - len(ids))}
            if token: p["pageToken"] = token
            d = self._api_get("playlistItems", p)
            for it in d.get("items", []):
                ids.append(it["contentDetails"]["videoId"])
            token = d.get("nextPageToken")
            if not token: break
        return ids

    def videos_stats(self, video_ids):
        """1 quota unit per batch of 50. Returns list of dicts with stats + publish time."""
        out = []
        for i in range(0, len(video_ids), 50):
            d = self._api_get("videos", {"part": "snippet,statistics", "id": ",".join(video_ids[i:i+50])})
            for it in d.get("items", []):
                sn, st = it.get("snippet", {}), it.get("statistics", {})
                out.append({"id": it["id"], "title": sn.get("title", ""), "channel": sn.get("channelTitle", ""),
                            "channel_id": sn.get("channelId", ""), "published": sn.get("publishedAt", ""),
                            "views": int(st.get("viewCount", 0) or 0), "likes": int(st.get("likeCount", 0) or 0),
                            "comments": int(st.get("commentCount", 0) or 0)})
        return out

    def latest_video_id(self):
        ch = self.my_channel()
        ids = self.playlist_video_ids(ch["uploads"], 1)
        if not ids: raise RuntimeError("Kênh chưa có video nào")
        return ids[0], ch

    def hot_videos(self, n=2):
        """Most-viewed recent uploads of MY channel (for inserting links into descriptions)."""
        ch = self.my_channel()
        ids = self.playlist_video_ids(ch["uploads"], 30)
        stats = self.videos_stats(ids)
        stats.sort(key=lambda x: x["views"], reverse=True)
        return stats[:n], ch

    def channel_by_handle(self, handle):
        h = handle.strip()
        if not h.startswith("@"): h = "@" + h.lstrip("@")
        d = self._api_get("channels", {"part": "snippet,contentDetails", "forHandle": h})
        items = d.get("items", [])
        if not items: return None
        it = items[0]
        return {"id": it["id"], "title": it["snippet"].get("title", ""),
                "uploads": it["contentDetails"]["relatedPlaylists"]["uploads"]}

    def channel_by_id(self, cid):
        d = self._api_get("channels", {"part": "snippet,contentDetails", "id": cid})
        items = d.get("items", [])
        if not items: return None
        it = items[0]
        return {"id": it["id"], "title": it["snippet"].get("title", ""),
                "uploads": it["contentDetails"]["relatedPlaylists"]["uploads"]}

    def update_snippet(self, video_id, title=None, description=None, tags=None, log=lambda m: None):
        """Push a new ORIGINAL title/description/tags (keeps category & other fields). 50 units."""
        snippet, _ = self.fetch_full(video_id)
        self._spend(1)
        body = {"id": video_id, "snippet": {
            "title": title if title is not None else snippet.get("title", ""),
            "description": description if description is not None else snippet.get("description", ""),
            "categoryId": snippet.get("categoryId", "22"),
            "tags": tags if tags is not None else (snippet.get("tags", []) or []),
            "defaultLanguage": snippet.get("defaultLanguage", "")}}
        if not body["snippet"]["defaultLanguage"]: body["snippet"].pop("defaultLanguage")
        r = self.s.put("https://www.googleapis.com/youtube/v3/videos", params={"part": "snippet"},
                       headers=self._auth_headers(), data=json.dumps(body, ensure_ascii=False).encode("utf-8"), timeout=40)
        self._spend(50)
        if r.status_code != 200: raise RuntimeError(f"Cập nhật tiêu đề/mô tả lỗi {r.status_code}: {r.text[:400]}")
        log(f"✏️ Đã cập nhật tiêu đề/mô tả/tags gốc của {video_id}")
        return True

    def insert_caption(self, video_id, lang_code, srt_text, log=lambda m: None):
        """Upload one .SRT caption track. NOTE: YouTube charges 400 quota units per caption."""
        meta = {"snippet": {"videoId": video_id, "language": lang_code, "name": "", "isDraft": False}}
        files = {"part": ("metadata", json.dumps(meta), "application/json"),
                 "media": ("subtitle.srt", srt_text.encode("utf-8"), "application/octet-stream")}
        r = self.s.post("https://www.googleapis.com/upload/youtube/v3/captions",
                        params={"part": "snippet", "uploadType": "multipart"},
                        headers={"Authorization": f"Bearer {self.access_token()}"}, files=files, timeout=60)
        self._spend(400)
        if r.status_code not in (200, 201): raise RuntimeError(f"Bắn phụ đề {lang_code} lỗi {r.status_code}: {r.text[:300]}")
        log(f"💬 Đã bắn phụ đề [{lang_code}] lên {video_id}")
        return True

    def post_comment(self, video_id, text, log=lambda m: None):
        body = {"snippet": {"videoId": video_id, "topLevelComment": {"snippet": {"textOriginal": text}}}}
        r = self.s.post("https://www.googleapis.com/youtube/v3/commentThreads", params={"part": "snippet"},
                        headers=self._auth_headers(), data=json.dumps(body, ensure_ascii=False).encode("utf-8"), timeout=30)
        self._spend(50)
        if r.status_code not in (200, 201): raise RuntimeError(f"Đăng comment lỗi {r.status_code}: {r.text[:300]}")
        log(f"💬 Đã đăng bình luận đầu tiên lên {video_id}")
        return True

    def search_channels(self, keyword, max_results=15):
        """Find channels by keyword via search.list — costs 100 units, use sparingly."""
        d = self._api_get("search", {"part": "snippet", "type": "channel", "q": keyword, "maxResults": max_results}, cost=100)
        out = []
        for it in d.get("items", []):
            cid = it["id"].get("channelId")
            if cid: out.append({"id": cid, "title": it["snippet"].get("title", "")})
        return out
