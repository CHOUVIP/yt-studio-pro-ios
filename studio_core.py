# -*- coding: utf-8 -*-
"""
studio_core.py — Studio layer for YT Studio Pro (© Nguyễn Đình Hà)
AI title/description/tag generation, competitor scanning, 24H health check,
anti-duplicate translation registry, daily quota counter, SRT building,
and Gemini video understanding (chapters + captions from a local video file).
"""
import os, re, json, time, datetime

REGISTRY_PATH = os.path.join(os.path.expanduser("~"), ".yt_studio_registry.json")
QUOTA_PATH = os.path.join(os.path.expanduser("~"), ".yt_studio_quota.json")

EMOTIONS = [
    ("asmr",   "😌 Thỏa mãn & ASMR", "oddly satisfying, pure ASMR, smooth and satisfying process"),
    ("wow",    "🤯 Kinh ngạc & Đột phá", "mind-blowing transformation, shocking before/after reveal"),
    ("curio",  "🧐 Tò mò & Độc dị", "curiosity, unique and unusual design, never seen before"),
    ("funny",  "😂 Hài hước", "funny, entertaining, playful moments"),
    ("heart",  "❤️ Cảm động", "heartwarming, emotional, meaningful story"),
    ("luxury", "💎 Sang trọng & Đẳng cấp", "luxury, premium, high-end craftsmanship"),
    ("fast",   "⚡ Nhanh & Giật gân", "fast-paced, extreme, record-breaking, intense"),
    ("skill",  "🏆 Tay nghề bậc thầy", "master craftsman skill, decades of experience, precision"),
]

# Language presets (YouTube localization codes), matching the reference tool's 40/20/12 sets.
PRESET_40 = ["en","es","hi","ar","pt-BR","ru","ja","id","fr","de","ko","it","tr","th","pl","nl","ur","uk","fa","bn","ta","te","mr","ml","pa","fil","ms","sv","ro","el","cs","hu","da","fi","no","iw","zh-CN","zh-TW","sr","bg"]
PRESET_20 = ["en","es","hi","ar","pt-BR","ru","ja","id","fr","de","ko","it","tr","th","pl","uk","fil","ms","zh-CN","vi"]
PRESET_12 = ["en","es","hi","ar","pt-BR","ru","ja","fr","de","ko","it","id"]

# ---------------------------------------------------------------- registry / quota
class Registry:
    """Anti-duplicate notebook: remembers which (video, language) pairs are already done,
    so re-running a video never re-translates / re-pushes the same language twice."""
    def __init__(self, path=REGISTRY_PATH):
        self.path = path; self.data = {}
        if os.path.exists(path):
            try: self.data = json.load(open(path, encoding="utf-8"))
            except Exception: self.data = {}
    def _save(self):
        try: json.dump(self.data, open(self.path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception: pass
    def has(self, video_id, lang_code):
        return lang_code in (self.data.get(video_id, {}).get("langs") or [])
    def mark(self, video_id, lang_codes, title=""):
        e = self.data.setdefault(video_id, {"langs": [], "title": "", "updated": ""})
        for c in lang_codes:
            if c not in e["langs"]: e["langs"].append(c)
        if title: e["title"] = title
        e["updated"] = datetime.datetime.now().isoformat(timespec="seconds")
        self._save()
    def stats(self):
        vids = len(self.data); langs = sum(len(v.get("langs") or []) for v in self.data.values())
        return vids, langs

class QuotaStore:
    """Daily YouTube API quota counter (default project quota = 10,000 units/day)."""
    def __init__(self, path=QUOTA_PATH):
        self.path = path; self.date = datetime.date.today().isoformat(); self.units = 0
        if os.path.exists(path):
            try:
                d = json.load(open(path, encoding="utf-8"))
                if d.get("date") == self.date: self.units = int(d.get("units", 0))
            except Exception: pass
    def add(self, n):
        today = datetime.date.today().isoformat()
        if today != self.date: self.date, self.units = today, 0
        self.units += int(n)
        try: json.dump({"date": self.date, "units": self.units}, open(self.path, "w", encoding="utf-8"))
        except Exception: pass

# ---------------------------------------------------------------- AI helpers
# Google retires Gemini models over time (gemini-3.8-flash died with a 404 in Nov 2026).
# Never depend on one model: walk a fallback chain, retrying transient 503/timeout.
GEMINI_FALLBACKS = ["gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.8-pro"]
GEMINI_RETIRED = {"gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash",
                  "gemini-1.5-flash-8b", "gemini-1.5-pro", "gemini-pro", "gemini-1.0-pro",
                  "gemini-2.5-pro", "gemini-2.5-flash"}
DEFAULT_GEMINI_MODEL = "gemini-3.5-flash"

_GEMINI_DAY_DEAD = {}   # model -> ISO date its free DAILY quota ran out (skip it all day)
def _gemini_429_info(r):
    """Classify a Gemini 429 from Google's error details: ('day'|'minute'|'', retry_seconds).
    A per-DAY free-tier quota is the common trap: preview models allow only a handful
    of requests/day, so the very first call of a step can already be 429."""
    try:
        err = (r.json() or {}).get("error", {})
        kind, retry = "", 0
        for d in err.get("details", []) or []:
            t = d.get("@type", "")
            if "RetryInfo" in t:
                try: retry = int(float(str(d.get("retryDelay", "0s")).rstrip("s") or 0))
                except Exception: retry = 0
            if "QuotaFailure" in t:
                for v in d.get("violations", []) or []:
                    q = (v.get("quotaId") or "") + " " + (v.get("quotaMetric") or "")
                    if "PerDay" in q: kind = "day"
                    elif "PerMinute" in q and not kind: kind = "minute"
        if not kind and err.get("status") == "RESOURCE_EXHAUSTED": kind = "minute"
        return kind, retry
    except Exception:
        return "", 0

def gemini_model_chain(cfg):
    m = (cfg.get("gemini_model") or "").strip()
    chain = []
    if m and m not in GEMINI_RETIRED: chain.append(m)
    if DEFAULT_GEMINI_MODEL not in chain: chain.append(DEFAULT_GEMINI_MODEL)
    for f in GEMINI_FALLBACKS:
        if f not in chain: chain.append(f)
    return chain

def gemini_generate(cfg, body, timeout=60, log=None, budget=260):
    """POST generateContent with a patient strategy:
    Phase 1 — one quick attempt per model in the chain; 404 = model dead, skip forever.
    Phase 2 — for models that answered (even 503 'high demand'), retry with growing
    waits (5/15/30/45/60s) until the total time budget runs out, logging every step.
    Returns (text, model_used). Raises a clear summary if Google stays overloaded."""
    import requests
    log = log or (lambda m: None)
    key = (cfg.get("gemini_key") or "").strip()
    chain = gemini_model_chain(cfg)
    t0 = time.monotonic(); waited = 0
    def elapsed(): return (time.monotonic() - t0) + waited
    last_err = {}
    retry_hint = {}
    def attempt(model):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            r = requests.post(url, params={"key": key}, json=body, timeout=timeout)
        except Exception as e:
            return ("busy", None, f"{type(e).__name__}: {str(e)[:90]}")
        if r.status_code == 200:
            try:
                txt = "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])
                if txt.strip(): return ("ok", txt, "")
                return ("busy", None, "trả về rỗng")
            except Exception as e:
                return ("busy", None, f"parse lỗi: {e}")
        if r.status_code == 404: return ("dead", None, f"HTTP 404 (model đã bị Google khai tử với key mới)")
        if r.status_code == 429:
            kind, retry = _gemini_429_info(r)
            if kind == "day": return ("daydead", None, "hết hạn mức NGÀY")
            if retry: retry_hint[model] = retry
            return ("busy", None, f"HTTP 429 (hết hạn mức theo phút — Google bảo chờ ~{retry or 20}s)")
        if r.status_code in (500, 502, 503, 504):
            return ("busy", None, f"HTTP {r.status_code} (Google đang quá tải)")
        return ("dead", None, f"HTTP {r.status_code}: {r.text[:130]}")
    import datetime as _dt
    today = _dt.date.today().isoformat()
    alive = []
    for model in chain:
        if _GEMINI_DAY_DEAD.get(model) == today:
            log(f"⏭️ {model}: đã hết hạn mức NGÀY hôm nay — bỏ qua cho đến khi Google reset hạn mức ngày")
            last_err[model] = "hết hạn mức ngày"; continue
        log(f"🤖 Đang gọi Gemini · model {model} ...")
        st, txt, err = attempt(model)
        if st == "ok": log(f"✅ Gemini trả kết quả (model {model})"); return txt, model
        last_err[model] = err
        if st == "daydead":
            _GEMINI_DAY_DEAD[model] = today
            log(f"⛔ {model}: HẾT HẠN MỨC NGÀY của gói Gemini miễn phí (gemini-3.5-flash chỉ ~20 lượt/ngày/project) — bỏ qua model này, chuyển model kế tiếp")
        elif st == "dead": log(f"⏭️ {model}: {err} — bỏ qua model này")
        else: alive.append(model); log(f"⚠️ {model}: {err}")
    rounds = [5, 15, 30, 45, 60, 60]
    tries = 1
    for wait in rounds:
        if not alive: break
        hint = max([retry_hint.get(m, 0) for m in alive] or [0])
        wait = min(max(wait, hint), 60)
        if elapsed() + wait > budget: break
        tries += 1
        log(f"⏳ Chờ {wait}s rồi thử lại Gemini (lần {tries})...")
        time.sleep(wait); waited += wait
        for model in list(alive):
            st, txt, err = attempt(model)
            if st == "ok": log(f"✅ Gemini trả kết quả (model {model}, lần {tries})"); return txt, model
            last_err[model] = err
            if st == "daydead":
                _GEMINI_DAY_DEAD[model] = today; alive.remove(model)
                log(f"⛔ {model}: HẾT HẠN MỨC NGÀY — bỏ qua, chuyển model kế tiếp")
            elif st == "dead": alive.remove(model); log(f"⏭️ {model}: {err} — bỏ qua")
            else: log(f"⚠️ {model}: {err}")
    detail = " | ".join(f"{m}: {e}" for m, e in last_err.items())
    if chain and all(_GEMINI_DAY_DEAD.get(m) == today for m in chain):
        raise RuntimeError("⛔ Gemini đã HẾT HẠN MỨC NGÀY (gói miễn phí) ở mọi model — hạn mức ngày của Google sẽ tự reset (xem AI Studio → Rate limits để biết hạn mức của key bạn). "
                           "Chạy tiếp ngay: (1) nhập OpenAI key ở tab 8 — app tự chuyển AI sang OpenAI, "
                           "(2) dùng Gemini key của một PROJECT Google khác (mỗi project một hạn mức riêng), (3) bật billing cho project của key này (rất rẻ).")
    raise RuntimeError(f"Gemini chưa trả kết quả sau ~{int(elapsed())}s thử lại. {detail}. "
                       f"Đây là quá tải phía Google (thường chỉ vài phút) — hãy thử lại sau ít phút, hoặc thêm OpenAI key ở tab 8 để có đường dự phòng.")

def _ai_ready(cfg):
    if (cfg.get("gemini_key") or "").strip(): return "gemini"
    if (cfg.get("openai_key") or "").strip(): return "openai"
    return ""

def ai_text(cfg, prompt, want_json=False, log=None):
    """One AI call: Gemini first (model fallback chain); if Gemini is unusable
    (quota/overload) and an OpenAI key exists, fall back to OpenAI for this call."""
    import requests
    log = log or (lambda m: None)
    kind = _ai_ready(cfg)
    if kind == "gemini":
        body = {"contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.8}}
        if want_json: body["generationConfig"]["responseMimeType"] = "application/json"
        try:
            txt, _model = gemini_generate(cfg, body, log=log)
            return txt
        except Exception as e:
            if not (cfg.get("openai_key") or "").strip(): raise
            log(f"🔁 Gemini không dùng được — tự chuyển sang OpenAI cho bước AI này. Lý do: {str(e)[:110]}")
    if (cfg.get("openai_key") or "").strip():
        model = cfg.get("openai_model") or "gpt-4o-mini"
        body = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.8}
        if want_json: body["response_format"] = {"type": "json_object"}
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers={"Authorization": f"Bearer {cfg['openai_key'].strip()}"}, json=body, timeout=120)
        if r.status_code != 200: raise RuntimeError(f"OpenAI lỗi {r.status_code}: {r.text[:300]}")
        log(f"✅ OpenAI trả kết quả (model {model})")
        return r.json()["choices"][0]["message"]["content"]
    raise RuntimeError("Chưa có Gemini/OpenAI API key — nhập key ở tab '🔑 API & Cài đặt' trước")

def _parse_json(text, list_key=None):
    """Parse AI JSON output tolerantly. Models (especially Lite ones) may return a
    bare array, an object followed by extra prose, or code fences. Strategy: try the
    whole text, then scan for the first balanced {...} or [...] block (string-aware)
    and parse that. A bare list is wrapped as {list_key: list} when list_key is given."""
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t).strip()
    def _wrap(v):
        if isinstance(v, list) and list_key: return {list_key: v}
        return v
    try: return _wrap(json.loads(t))
    except Exception: pass
    for start, ch in enumerate(t):
        if ch not in "{[": continue
        close_c = "}" if ch == "{" else "]"
        depth, in_str, esc = 0, False, False
        for i in range(start, len(t)):
            c = t[i]
            if in_str:
                if esc: esc = False
                elif c == "\\": esc = True
                elif c == '"': in_str = False
                continue
            if c == '"': in_str = True
            elif c == ch: depth += 1
            elif c == close_c:
                depth -= 1
                if depth == 0:
                    try: return _wrap(json.loads(t[start:i+1]))
                    except Exception: break
    raise ValueError(f"AI trả về không phải JSON hợp lệ (đầu đoạn: {t[:120]!r})")

def _emotion_text(emotion_keys):
    m = {k: v for k, _, v in EMOTIONS}
    return "; ".join(m[k] for k in emotion_keys if k in m)

def gen_titles(cfg, orig_title, product, emotion_keys, niche="", log=None):
    prompt = f"""You are a YouTube title strategist for a {niche or 'DIY/craft'} channel.
Original title: "{orig_title}"
Product/material/technique actually in the video: {product or '(unknown — infer from title)'}
Dominant emotions to inject: {_emotion_text(emotion_keys) or 'satisfying craftsmanship'}
Create EXACTLY 3 NEW English title options. Rules:
- Each title MUST be 70–80 characters long (count carefully), clean, no clickbait lies, no ALL CAPS spam, max 1 emoji at the end if natural.
- Front-load the strongest hook in the first 40 characters.
- Predict a CTR score (0–100) for each, realistically.
- Also give a short Vietnamese translation of each title and a 2–4 word "thumbnail hook" text.
Reply with ONLY this JSON: {{"titles":[{{"title":"...","vi":"...","ctr":82,"hook":"..."}}]}}"""
    data = _parse_json(ai_text(cfg, prompt, want_json=True, log=log), list_key="titles")
    out = []
    for t in (data.get("titles") or [])[:3]:
        if isinstance(t, str): t = {"title": t}
        out.append({"title": str(t.get("title", "")).strip(), "vi": str(t.get("vi", "")).strip(),
                    "ctr": int(t.get("ctr", 0) or 0), "hook": str(t.get("hook", "")).strip()})
    if not out: raise RuntimeError("AI không trả về tiêu đề nào — thử lại")
    return out

def gen_description(cfg, title, product, emotion_keys, orig_desc="", log=None):
    prompt = f"""You are a YouTube SEO copywriter. Write the FULL description (English) for this video.
Title: "{title}"
Product/material/technique: {product or '(infer from title)'}
Emotions: {_emotion_text(emotion_keys) or 'satisfying craftsmanship'}
Original description for reference (may be empty): {(orig_desc or '')[:800]}
Structure: 2–3 hook lines with the main keywords in the first 2 lines; a short paragraph about the process; a CHAPTERS section with 5–8 timestamps starting at 0:00 spread across a typical video; a closing line inviting subscribe; 3–5 hashtags at the very end.
Also produce 12–15 SEO tags (no # sign).
Reply with ONLY this JSON: {{"description":"...","tags":["..."],"chapters":[{{"time":"0:00","name":"..."}}]}}"""
    data = _parse_json(ai_text(cfg, prompt, want_json=True, log=log))
    return {"description": str(data.get("description", "")).strip(),
            "tags": [str(t).strip() for t in (data.get("tags") or []) if str(t).strip()],
            "chapters": data.get("chapters") or []}

def gen_ideas(cfg, niche, hit_titles, log=None):
    hits = "\n".join(f"- {t}" for t in hit_titles[:12]) or "(no data)"
    prompt = f"""You are a YouTube content strategist for a {niche or 'DIY/craft'} channel.
Competitor videos exploding right now:
{hits}
Suggest 5 concrete next-video ideas that ride these proven patterns but with a fresh twist.
Reply with ONLY this JSON: {{"ideas":[{{"idea":"...","why":"..."}}]}} (why = one short Vietnamese sentence)"""
    data = _parse_json(ai_text(cfg, prompt, want_json=True, log=log), list_key="ideas")
    return [{"idea": str(i.get("idea", "")).strip(), "why": str(i.get("why", "")).strip()}
            for i in ((x if isinstance(x, dict) else {"idea": x}) for x in (data.get("ideas") or [])[:5])
            if str(i.get("idea", "")).strip()]

# ---------------------------------------------------------------- chapters / SRT
_TS_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?\s+(.+)$")
def chapters_from_text(text):
    out = []
    for line in (text or "").splitlines():
        m = _TS_RE.match(line.strip())
        if m:
            if m.group(3): sec = int(m.group(1))*3600 + int(m.group(2))*60 + int(m.group(3)); name = m.group(4)
            else: sec = int(m.group(1))*60 + int(m.group(2)); name = m.group(4)
            out.append((sec, name.strip()))
    return out

def _srt_ts(sec):
    sec = max(0, int(sec)); h, rem = divmod(sec, 3600); m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d},000"

def build_srt(chapters, default_len=25):
    """chapters: list of (start_sec, text). Each caption lasts until the next chapter."""
    if not chapters: return ""
    chapters = sorted(chapters)
    lines = []
    for i, (start, text) in enumerate(chapters):
        end = chapters[i+1][0] if i+1 < len(chapters) else start + default_len
        if end <= start: end = start + default_len
        lines.append(f"{i+1}\n{_srt_ts(start)} --> {_srt_ts(end)}\n{text}\n")
    return "\n".join(lines)

# ---------------------------------------------------------------- competitors / health
def _parse_dt(s):
    try: return datetime.datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except Exception: return None

def views_per_hour(stat, now=None):
    pub = _parse_dt(stat.get("published", ""))
    if not pub: return 0.0, 0.0
    now = now or datetime.datetime.now(datetime.timezone.utc)
    age_h = max(1.0, (now - pub).total_seconds() / 3600.0)
    return stat["views"] / age_h, age_h

def scan_competitors(uploader, handles, days=7, per_channel=12, log=lambda m: None):
    """Zero-search scan: resolve each @handle (1 unit), read its uploads (1 unit),
    batch stats (1 unit). Returns rows sorted by views/hour desc."""
    rows = []
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    for h in handles:
        h = (h or "").strip()
        if not h: continue
        try:
            ch = uploader.channel_by_handle(h) if not h.startswith("UC") else uploader.channel_by_id(h)
            if not ch: log(f"⚠️ Không tìm thấy kênh {h}"); continue
            ids = uploader.playlist_video_ids(ch["uploads"], per_channel)
            stats = uploader.videos_stats(ids)
            fresh = [s for s in stats if (_parse_dt(s["published"]) or cutoff) >= cutoff]
            vphs = sorted((views_per_hour(s)[0] for s in fresh), reverse=True)
            median = vphs[len(vphs)//2] if vphs else 0.0
            for s in fresh:
                vph, age_h = views_per_hour(s)
                rows.append({**s, "vph": round(vph, 1), "age_h": round(age_h, 1),
                             "explode": bool(vph >= max(3*median, median + 50) and s["views"] >= 500)})
            log(f"🔎 {ch['title']}: {len(fresh)} video trong {days} ngày")
        except Exception as e:
            log(f"⚠️ Quét {h} lỗi: {e}")
    rows.sort(key=lambda r: r["vph"], reverse=True)
    return rows

def health_check(uploader, video_id):
    stats = uploader.videos_stats([video_id])
    if not stats: raise RuntimeError("Không lấy được thống kê video")
    s = stats[0]
    vph, age_h = views_per_hour(s)
    ch = uploader.my_channel()
    ids = uploader.playlist_video_ids(ch["uploads"], 20)
    others = [x for x in uploader.videos_stats(ids) if x["id"] != video_id]
    avg = sum(views_per_hour(x)[0] for x in others) / len(others) if others else 0.0
    ratio = (vph / avg) if avg else 0.0
    if age_h < 24: verdict = "⏳ Video chưa đủ 24H — chờ thêm rồi hãy kết luận"
    elif ratio >= 1.2: verdict = "🟢 Đang khỏe — view/giờ cao hơn trung bình kênh, cứ để YouTube đề xuất tiếp"
    elif ratio >= 0.7: verdict = "🟡 Trung bình — ngang kênh; có thể thử đổi thumbnail trước"
    else: verdict = "🔴 Yếu — view/giờ thấp hơn hẳn trung bình kênh, nên CỨU CTR: đổi tiêu đề + dịch lại đa ngôn ngữ"
    return {"video": s, "vph": round(vph, 1), "age_h": round(age_h, 1), "views": s["views"],
            "channel_avg_vph": round(avg, 1), "ratio": round(ratio, 2), "verdict": verdict}

# ---------------------------------------------------------------- Gemini video understanding
def gemini_video_chapters(cfg, path, log=lambda m: None):
    """Upload a local video to Gemini Files API and ask for chapters + an SRT caption
    track describing the visuals (for silent DIY/craft videos). Returns (chapters_text, srt_text)."""
    import requests
    key = (cfg.get("gemini_key") or "").strip()
    if not key: raise RuntimeError("Chức năng xem video cần Gemini API key")
    model = cfg.get("gemini_model") or "gemini-3.8-flash"
    size = os.path.getsize(path)
    mime = {".mp4": "video/mp4", ".mov": "video/quicktime", ".mkv": "video/x-matroska",
            ".webm": "video/webm", ".avi": "video/x-msvideo"}.get(os.path.splitext(path)[1].lower(), "video/mp4")
    log(f"🎞️ Đang tải video lên Gemini ({size/1e6:.1f} MB)...")
    r = requests.post("https://generativelanguage.googleapis.com/upload/v1beta/files", params={"key": key},
                      headers={"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                               "X-Goog-Upload-Header-Content-Length": str(size),
                               "X-Goog-Upload-Header-Content-Type": mime, "Content-Type": "application/json"},
                      json={"file": {"display_name": os.path.basename(path)}}, timeout=60)
    if r.status_code != 200: raise RuntimeError(f"Gemini upload start lỗi {r.status_code}: {r.text[:250]}")
    up_url = r.headers.get("x-goog-upload-url")
    with open(path, "rb") as f: data = f.read()
    r = requests.post(up_url, headers={"Content-Length": str(size), "X-Goog-Upload-Offset": "0",
                                       "X-Goog-Upload-Command": "upload, finalize"}, data=data, timeout=900)
    if r.status_code not in (200, 201): raise RuntimeError(f"Gemini upload lỗi {r.status_code}: {r.text[:250]}")
    finfo = r.json().get("file", {})
    name, uri = finfo.get("name", ""), finfo.get("uri", "")
    for _ in range(60):
        if finfo.get("state") == "ACTIVE": break
        time.sleep(5)
        rr = requests.get(f"https://generativelanguage.googleapis.com/v1beta/{name}", params={"key": key}, timeout=30)
        finfo = rr.json(); uri = finfo.get("uri", uri)
    if finfo.get("state") != "ACTIVE": raise RuntimeError("Gemini xử lý video quá lâu — thử lại sau")
    log("🎞️ Gemini đang xem video và chia chapters + viết phụ đề...")
    prompt = """Watch this video carefully. Reply with ONLY this JSON:
{"chapters":[{"time":"0:00","name":"short chapter title in English"}],
 "srt":"a complete SRT subtitle track (numbered, timestamps) with short English captions describing what is visibly happening on screen, one caption every 5-15 seconds"}
Chapters: 5-10 entries following the real workflow shown. Captions must match the actual visuals and timing."""
    body = {"contents": [{"parts": [{"file_data": {"mime_type": mime, "file_uri": uri}}, {"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4}}
    txt, _used = gemini_generate(cfg, body, timeout=600, log=log, budget=1200)
    data = _parse_json(txt)
    ch_txt = "\n".join(f"{c.get('time','0:00')} {c.get('name','')}" for c in (data.get("chapters") or []))
    return ch_txt, str(data.get("srt", "")).strip()
