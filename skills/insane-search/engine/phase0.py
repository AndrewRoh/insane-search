"""Phase 0 — official public-API router (the SANCTIONED exception to No-Site-Name).

Per SKILL.md R5, platforms that publish official no-auth public endpoints get a
deterministic route tried BEFORE the generic WAF grid. This is the *enforced,
in-engine* version of what used to be agent-driven curl snippets in SKILL.md —
so the agent can no longer silently skip it (which is exactly how Reddit/X were
wrongly declared "blocked": the grid 403'd on `.json` and nobody tried `.rss`).

This file is the ONLY engine/ module allowed to name platform hosts; it is
exempted in `bias_check.EXPLICIT_ALLOW_FILES`. Do NOT add per-site logic to any
other engine file — generic WAF handling stays site-agnostic.

Contract:
    route(url) -> Optional[dict]
      None              → url is not a recognised Phase-0 platform; caller runs
                          the generic grid as usual.
      {"platform","ok","route","content","final_url","attempts":[...]}
                        → recognised platform. `ok` says whether an official
                          route succeeded. Even on ok=False the caller should
                          fall through to the grid, but `attempts` is recorded
                          so failure is never silent.

Each attempt dict: {"route","platform","ok","status","bytes","note"}.
"""
from __future__ import annotations

import re
import subprocess
from typing import Optional
from urllib.parse import urlsplit


# --- low-level helpers -------------------------------------------------------
def _cffi_get(url: str, *, impersonate: str = "safari", timeout: int = 15):
    from curl_cffi import requests as r  # lazy: engine works even if missing
    return r.get(
        url,
        impersonate=impersonate,  # type: ignore[arg-type]
        timeout=timeout,
        headers={
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
        },
        allow_redirects=True,
    )


def _host(url: str) -> str:
    h = (urlsplit(url).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h  # strip the literal "www." prefix only


def _attempt(platform: str, route: str, ok: bool, status: int, body: str, note: str = "") -> dict:
    return {"platform": platform, "route": route, "ok": ok, "status": status,
            "bytes": len(body or ""), "note": note}


# --- platform detectors ------------------------------------------------------
def _detect(url: str) -> Optional[str]:
    h = _host(url)
    if not h:
        return None
    if "reddit.com" in h or h == "redd.it":
        return "reddit"
    if h in ("x.com", "twitter.com") or h.endswith(".x.com") or h.endswith(".twitter.com"):
        return "x"
    if "youtube.com" in h or h == "youtu.be":
        return "youtube"
    return None


# --- reddit ------------------------------------------------------------------
def _reddit(url: str, timeout: int) -> dict:
    attempts: list[dict] = []
    base = url.split("?", 1)[0].rstrip("/")
    # Build an .rss / .json target from the path (works for /r/<sub> and post URLs).
    rss_url = base + ("/.rss" if "/comments/" not in base else ".rss")
    json_url = base + ("/.json" if "/comments/" not in base else ".json")

    # Route 1: RSS (the route that actually survives — Reddit gates the JSON API).
    try:
        x = _cffi_get(rss_url, timeout=timeout)
        ok = x.status_code == 200 and ("<rss" in x.text or "<feed" in x.text)
        attempts.append(_attempt("reddit", "rss", ok, x.status_code, x.text,
                                 "feed" if ok else "no-feed-markers"))
        if ok:
            return {"platform": "reddit", "ok": True, "route": "rss",
                    "content": x.text, "final_url": rss_url, "attempts": attempts}
    except Exception as e:
        attempts.append(_attempt("reddit", "rss", False, 0, "", f"{type(e).__name__}"))

    # Route 2: JSON via curl_cffi (often 403 now, but try — cheap).
    try:
        x = _cffi_get(json_url, timeout=timeout)
        ok = x.status_code == 200 and x.text.lstrip().startswith(("{", "["))
        attempts.append(_attempt("reddit", "json", ok, x.status_code, x.text,
                                 "json" if ok else f"status={x.status_code}"))
        if ok:
            return {"platform": "reddit", "ok": True, "route": "json",
                    "content": x.text, "final_url": json_url, "attempts": attempts}
    except Exception as e:
        attempts.append(_attempt("reddit", "json", False, 0, "", f"{type(e).__name__}"))

    return {"platform": "reddit", "ok": False, "route": None, "content": "",
            "final_url": url, "attempts": attempts}


# --- x / twitter -------------------------------------------------------------
_TWEET_ID_RE = re.compile(r"/status(?:es)?/(\d+)")


def _x(url: str, timeout: int) -> dict:
    attempts: list[dict] = []
    m = _TWEET_ID_RE.search(url)

    if m:  # single tweet → tweet-result + oembed (both no-auth, reliable)
        tid = m.group(1)
        try:
            x = _cffi_get(f"https://cdn.syndication.twimg.com/tweet-result?id={tid}&token=a", timeout=timeout)
            d = x.json() if x.status_code == 200 else {}
            ok = bool(d.get("text"))
            attempts.append(_attempt("x", "tweet-result", ok, x.status_code, x.text,
                                     "has-text" if ok else f"status={x.status_code}"))
            if ok:
                return {"platform": "x", "ok": True, "route": "tweet-result",
                        "content": x.text, "final_url": url, "attempts": attempts}
        except Exception as e:
            attempts.append(_attempt("x", "tweet-result", False, 0, "", f"{type(e).__name__}"))
        try:
            ourl = f"https://publish.twitter.com/oembed?url=https://twitter.com/i/status/{tid}&omit_script=1"
            x = _cffi_get(ourl, timeout=timeout)
            d = x.json() if x.status_code == 200 else {}
            ok = bool(d.get("html"))
            attempts.append(_attempt("x", "oembed", ok, x.status_code, x.text,
                                     "has-html" if ok else f"status={x.status_code}"))
            if ok:
                return {"platform": "x", "ok": True, "route": "oembed",
                        "content": x.text, "final_url": ourl, "attempts": attempts}
        except Exception as e:
            attempts.append(_attempt("x", "oembed", False, 0, "", f"{type(e).__name__}"))
    else:  # profile timeline → syndication (rate-limit-prone; retry once)
        handle = urlsplit(url).path.strip("/").split("/")[0]
        _reserved = {"i", "search", "home", "explore", "messages", "notifications", "settings", "hashtag"}
        if handle and handle.lower() not in _reserved:
            surl = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"
            for attempt_no in range(2):
                try:
                    x = _cffi_get(surl, timeout=timeout)
                    ok = x.status_code == 200 and "__NEXT_DATA__" in x.text
                    attempts.append(_attempt("x", f"syndication-timeline#{attempt_no+1}", ok,
                                             x.status_code, x.text,
                                             "timeline" if ok else f"status={x.status_code}"))
                    if ok:
                        return {"platform": "x", "ok": True, "route": "syndication-timeline",
                                "content": x.text, "final_url": surl, "attempts": attempts}
                except Exception as e:
                    attempts.append(_attempt("x", f"syndication-timeline#{attempt_no+1}", False, 0, "", f"{type(e).__name__}"))

    return {"platform": "x", "ok": False, "route": None, "content": "",
            "final_url": url, "attempts": attempts}


# --- youtube -----------------------------------------------------------------
def _youtube(url: str, timeout: int) -> dict:
    import sys
    import json
    attempts: list[dict] = []
    
    cmd_candidates = [
        ["yt-dlp", "--dump-json", "--skip-download", url],
        [sys.executable, "-m", "yt_dlp", "--dump-json", "--skip-download", url],
        ["python", "-m", "yt_dlp", "--dump-json", "--skip-download", url],
        ["python3", "-m", "yt_dlp", "--dump-json", "--skip-download", url],
    ]
    
    meta_json = None
    last_err = ""
    for cmd in cmd_candidates:
        try:
            p = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=max(timeout, 60),
                encoding="utf-8",
            )
            if p.returncode == 0 and p.stdout.strip().startswith("{"):
                meta_json = p.stdout.strip()
                break
            else:
                last_err = p.stderr or f"exit code {p.returncode}"
        except FileNotFoundError:
            last_err = "FileNotFoundError"
            continue
        except Exception as e:
            last_err = str(e)
            continue
            
    if not meta_json:
        attempts.append(_attempt("youtube", "yt-dlp", False, 0, "", f"Failed to run yt-dlp: {last_err}"))
        return {"platform": "youtube", "ok": False, "route": None, "content": "",
                "final_url": url, "attempts": attempts}

    try:
        meta = json.loads(meta_json)
        title = meta.get("title", "Unknown Title")
        channel = meta.get("uploader", "Unknown Channel")
        desc = meta.get("description", "")
        
        # Subtitle fetching
        sub_text = ""
        auto_caps = meta.get("automatic_captions", {}) or {}
        subs = meta.get("subtitles", {}) or {}
        
        # Find ko first, then en
        chosen_lang = None
        chosen_list = None
        if "ko" in auto_caps:
            chosen_lang, chosen_list = "ko", auto_caps["ko"]
        elif "ko" in subs:
            chosen_lang, chosen_list = "ko", subs["ko"]
        elif "en" in auto_caps:
            chosen_lang, chosen_list = "en", auto_caps["en"]
        elif "en" in subs:
            chosen_lang, chosen_list = "en", subs["en"]
            
        if chosen_list:
            # find json3 url
            sub_url = None
            for item in chosen_list:
                if item.get("ext") == "json3":
                    sub_url = item.get("url")
                    break
            if not sub_url:
                # fallback to first url
                sub_url = chosen_list[0].get("url")
                
            if sub_url:
                try:
                    res = _cffi_get(sub_url, timeout=timeout)
                    if res.status_code == 200:
                        if "json3" in sub_url or res.text.lstrip().startswith("{"):
                            # Parse json3
                            sub_data = res.json()
                            texts = []
                            for ev in sub_data.get("events", []):
                                if "segs" in ev:
                                    seg_text = "".join(seg.get("utf8", "") for seg in ev["segs"])
                                    seg_text = seg_text.strip()
                                    if seg_text:
                                        texts.append(seg_text)
                            sub_text = " ".join(texts)
                        else:
                            # vtt or other plain parsing
                            lines = res.text.splitlines()
                            clean_lines = []
                            seen = set()
                            for line in lines:
                                line = line.strip()
                                if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:") or "-->" in line:
                                    continue
                                line = re.sub(r'<[^>]+>', '', line)
                                if line in seen:
                                    continue
                                seen.add(line)
                                clean_lines.append(line)
                            sub_text = " ".join(clean_lines)
                except Exception as e:
                    sub_text = f"(Failed to fetch subtitles: {str(e)})"
        
        # Build clean output content
        output_parts = [
            f"Title: {title}",
            f"Channel: {channel}",
            f"Description: {desc}",
            f"\n--- Subtitles ({chosen_lang or 'None'}) ---",
            sub_text or "(No subtitles found)"
        ]
        content = "\n".join(output_parts)
        
        attempts.append(_attempt("youtube", "yt-dlp", True, 200, content, f"Subtitles loaded: {chosen_lang}"))
        return {"platform": "youtube", "ok": True, "route": "yt-dlp",
                "content": content, "final_url": url, "attempts": attempts}
                
    except Exception as e:
        attempts.append(_attempt("youtube", "yt-dlp", False, 0, "", f"Parsing error: {str(e)}"))
        return {"platform": "youtube", "ok": False, "route": None, "content": "",
                "final_url": url, "attempts": attempts}


_ROUTERS = {"reddit": _reddit, "x": _x, "youtube": _youtube}


# --- public entrypoint -------------------------------------------------------
def route(url: str, *, timeout: int = 15) -> Optional[dict]:
    platform = _detect(url)
    if platform is None:
        return None
    return _ROUTERS[platform](url, timeout)
