"""Deck research — internet-first source collection for slide generation.

Collects material from the OPEN WEB only (no PubMed-style databases):
  1. PDF books / lecture notes  → download → pypdf → PyMuPDF → OCR extraction
  2. SlideShare presentations   → page transcript (full slide text) scraping
  3. Open notes / HTML pages    → readable text extraction

Everything lands in a job-local corpus with title+URL provenance so the
assembled deck can cite its sources.
"""
import logging
import re
import time
import html as html_mod
from urllib.parse import quote_plus, urlparse

import requests

log = logging.getLogger("slides.research")

_JUNK_DOMAINS = ("youtube.com", "zhihu.com", "facebook.com", "instagram.com", "twitter.com",
                 "x.com", "tiktok.com", "pinterest.com", "quora.com", "reddit.com",
                 "support.google.com", "accounts.google", "play.google")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 20
MAX_DOC_CHARS = 60_000   # per source
MAX_CORPUS_CHARS = 400_000


def _get(url: str, **kw) -> requests.Response | None:
    try:
        r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": UA}, **kw)
        if r.status_code == 200:
            return r
        log.debug("GET %s -> %s", url, r.status_code)
    except Exception as e:
        log.debug("GET %s failed: %s", url, e)
    return None


# ── 1. Web search (DuckDuckGo HTML — no API key) ─────────────────────────────

def web_search(query: str, limit: int = 8) -> list[dict]:
    """Anonymous web search — DuckDuckGo HTML, DDG lite, then Bing HTML
    (each engine throttles; the chain keeps research alive when one blocks)."""
    results = _search_ddg_html(query, limit)
    if len(results) < 3:
        results += _search_ddg_lite(query, limit - len(results))
    if len(results) < 3:
        results += _search_bing(query, limit - len(results))
    return results[:limit]


def _search_ddg_html(query: str, limit: int) -> list[dict]:
    r = _get(f"https://html.duckduckgo.com/html/?q={quote_plus(query)}")
    if not r:
        return []
    results, seen = [], set()
    for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', r.text, re.S):
        url, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        qm = re.search(r"[?&]uddg=([^&]+)", url)
        if qm:
            from urllib.parse import unquote
            url = unquote(qm.group(1))
        if url in seen or not url.startswith("http"):
            continue
        seen.add(url)
        results.append({"url": url, "title": html_mod.unescape(title).strip()[:200]})
        if len(results) >= limit:
            break
    return results


def _search_ddg_lite(query: str, limit: int) -> list[dict]:
    if limit <= 0:
        return []
    r = _get(f"https://lite.duckduckgo.com/lite/?q={quote_plus(query)}")
    if not r:
        return []
    results, seen = [], set()
    for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*class="result-link"[^>]*>(.*?)</a>', r.text, re.S):
        url, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
        if url in seen or "duckduckgo.com" in url:
            continue
        seen.add(url)
        results.append({"url": url, "title": html_mod.unescape(title).strip()[:200]})
        if len(results) >= limit:
            break
    return results


def _bing_unwrap(url: str) -> str:
    """Decode Bing's /ck/a redirect to the real target (u=a1<base64url>)."""
    if "/ck/a" not in url:
        return url
    from urllib.parse import unquote, parse_qs, urlparse
    try:
        q = parse_qs(urlparse(html_mod.unescape(url)).query)
        u = (q.get("u") or [""])[0]
        if u.startswith("a1") or u.startswith("a2"):
            import base64
            padded = u[2:] + "=" * (-len(u[2:]) % 4)
            return base64.urlsafe_b64decode(padded).decode("utf-8", errors="ignore")
    except Exception:
        pass
    return url


def _search_bing(query: str, limit: int) -> list[dict]:
    if limit <= 0:
        return []
    r = _get(f"https://www.bing.com/search?q={quote_plus(query)}&setlang=en&cc=US&count=15")
    if not r:
        return []
    results, seen = [], set()
    for m in re.finditer(r'<h2><a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a></h2>', r.text, re.S):
        url = _bing_unwrap(m.group(1))
        title = re.sub(r"<[^>]+>", "", m.group(2))
        if url in seen or not url.startswith("http"):
            continue
        low = url.lower()
        if any(d in low for d in _JUNK_DOMAINS):
            continue
        seen.add(url)
        results.append({"url": url, "title": html_mod.unescape(title).strip()[:200]})
        if len(results) >= limit:
            break
    return results


# ── 2. SlideShare transcripts ────────────────────────────────────────────────

def slideshare_transcript(url: str) -> dict | None:
    """Extract the FULL slide transcript + metadata from a SlideShare page.

    SlideShare embeds every slide's text in the page (JSON / transcript
    blocks), publicly and anonymously — the raw .pptx download is
    login-gated, but the transcript is exactly what content generation needs.
    """
    r = _get(url)
    if not r:
        return None
    page = r.text
    title = None
    mt = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', page) or \
         re.search(r'<title>(.*?)</title>', page, re.S)
    if mt:
        title = html_mod.unescape(mt.group(1)).split("|")[0].strip()[:200]
    # transcript lines appear as JSON string arrays in several shapes
    lines: list[str] = []
    for arr in re.finditer(r'"transcript"\s*:\s*(\[[^\]]{40,}\])', page):
        try:
            import json
            vals = json.loads(arr.group(1).replace("\\'", "'"))
            if isinstance(vals, list):
                lines.extend(str(v) for v in vals if str(v).strip())
        except Exception:
            pass
    if not lines:  # HTML transcript blocks fallback
        for m in re.finditer(r'<p[^>]*class="transcript[^"]*"[^>]*>(.*?)</p>', page, re.S):
            lines.append(html_mod.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip())
    if not lines:  # slide titles from the JSON slide list
        for m in re.finditer(r'"title"\s*:\s*"((?:[^"\\]|\\.){15,120})"', page):
            lines.append(m.group(1).encode().decode("unicode_escape", errors="ignore"))
    text = "\n".join(l for l in lines if l)[:MAX_DOC_CHARS]
    if len(text) < 120:
        return None
    return {"kind": "slideshare", "title": title or "SlideShare deck", "url": url, "text": text}


# ── 3. PDF download + 3-tier extraction (pypdf → PyMuPDF → OCR) ─────────────

def fetch_pdf_text(url: str) -> dict | None:
    """Download a PDF and extract text using faculty_tools' proven chain."""
    r = _get(url)
    if not r or not r.content[:5].startswith(b"%PDF"):
        return None
    import base64
    from api.faculty_tools import _extract_text_from_file
    try:
        text = _extract_text_from_file(base64.b64encode(r.content).decode(), "source.pdf")
    except Exception as e:
        log.debug("pdf extract failed %s: %s", url, e)
        return None
    text = (text or "").strip()[:MAX_DOC_CHARS]
    if len(text) < 300:
        return None
    return {"kind": "pdf", "title": _title_from_url(url), "url": url, "text": text}


# ── 4. Open notes / HTML pages → readable text ───────────────────────────────

_TAG_RE = re.compile(r"<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>", re.S | re.I)


def fetch_page_text(url: str) -> dict | None:
    r = _get(url)
    if not r:
        return None
    ctype = r.headers.get("content-type", "")
    if "pdf" in ctype:
        return fetch_pdf_text(url)
    if "html" not in ctype and "text" not in ctype:
        return None
    page = _TAG_RE.sub(" ", r.text)
    text = html_mod.unescape(re.sub(r"<[^>]+>", " ", page))
    text = re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n", text)).strip()
    # keep the meaty middle: drop very short pages
    if len(text) < 800:
        return None
    mt = re.search(r"<title>(.*?)</title>", r.text, re.S)
    title = html_mod.unescape(mt.group(1)).strip()[:200] if mt else _title_from_url(url)
    return {"kind": "page", "title": title, "url": url, "text": text[:MAX_DOC_CHARS]}


def _title_from_url(url: str) -> str:
    last = [p for p in urlparse(url).path.split("/") if p][-1:]
    return (last[0][:80] if last else url)[:120]


# ── 5. Guaranteed open sources: Wikipedia + Wikibooks (official APIs) ────────

def _wiki_api(host: str, params: dict) -> dict | None:
    try:
        r = _get(f"https://{host}/w/api.php", params={**params, "format": "json"})
        return r.json() if r else None
    except Exception:
        return None


def wikipedia_sources(topic: str, max_pages: int = 3) -> list[dict]:
    """Full plain-text extracts of the top matching Wikipedia pages (open API)."""
    q = _wiki_api("en.wikipedia.org", {"action": "query", "list": "search", "srlimit": max_pages, "srsearch": topic})
    out = []
    if not q:
        return out
    for hit in (q.get("query", {}).get("search") or [])[:max_pages]:
        title = hit.get("title", "")
        ext = _wiki_api("en.wikipedia.org", {"action": "query", "prop": "extracts",
                                             "explaintext": 1, "exlimit": 1, "titles": title})
        pages = (ext or {}).get("query", {}).get("pages", {})
        text = next(iter(pages.values()), {}).get("extract", "") if pages else ""
        if len(text) > 500:
            out.append({"kind": "wikipedia", "title": f"Wikipedia: {title}",
                        "url": f"https://en.wikipedia.org/wiki/{quote_plus(title.replace(' ', '_'))}",
                        "text": text[:MAX_DOC_CHARS]})
    return out


def wikibooks_sources(topic: str, max_pages: int = 2) -> list[dict]:
    """Chapters from Wikibooks — open textbooks (official API)."""
    q = _wiki_api("en.wikibooks.org", {"action": "query", "list": "search", "srlimit": max_pages, "srsearch": topic})
    out = []
    if not q:
        return out
    for hit in (q.get("query", {}).get("search") or [])[:max_pages]:
        title = hit.get("title", "")
        ext = _wiki_api("en.wikibooks.org", {"action": "query", "prop": "extracts",
                                             "explaintext": 1, "exlimit": 1, "titles": title})
        pages = (ext or {}).get("query", {}).get("pages", {})
        text = next(iter(pages.values()), {}).get("extract", "") if pages else ""
        if len(text) > 500:
            out.append({"kind": "wikibooks", "title": f"Wikibooks: {title}",
                        "url": f"https://en.wikibooks.org/wiki/{quote_plus(title.replace(' ', '_'))}",
                        "text": text[:MAX_DOC_CHARS]})
    return out


# ── Orchestration ─────────────────────────────────────────────────────────────

def _relevant(hit: dict, topic: str) -> bool:
    """Keep education-relevant hits: pdf/slideshare always pass; others must
    share a meaningful topic token (stops 'DPP'→Canon style mismatches)."""
    low = (hit["url"] + " " + hit["title"]).lower()
    if low.endswith(".pdf") or ".pdf?" in low or "slideshare.net" in low or "ocw." in low or "edu" in low:
        return True
    tokens = [t for t in re.split(r"[^a-z0-9-]+", topic.lower()) if len(t) > 4]
    return any(t in low for t in tokens)


def collect_sources(topic: str, target_chars: int = 250_000, progress_cb=None) -> list[dict]:
    """Collect an internet corpus for a deck topic.

    Queries mix lecture-note / pdf / slideshare intents, then downloads the
    best-looking hits until the corpus target is reached. Sources with more
    text win; provenance kept for citations.
    """
    q = f'"{topic}"' if len(topic.split()) > 2 else topic
    intents = [
        f'{q} lecture notes pdf',
        f'{q} filetype:pdf',
        f'{topic} site:slideshare.net',
        f'{q} ppt presentation',
        f'{q} study notes',
    ]
    corpus: list[dict] = []
    have = set()
    total = 0
    # guaranteed open-API base (works even when search engines throttle)
    for base in (wikipedia_sources, wikibooks_sources):
        if progress_cb:
            progress_cb(f"collecting {base.__name__}…")
        for doc in base(topic):
            if doc["url"] not in have:
                have.add(doc["url"]); corpus.append(doc); total += len(doc["text"])
    for qi, q in enumerate(intents):
        if total >= target_chars:
            break
        if progress_cb:
            progress_cb(f"searching: {q}")
        time.sleep(1.2)  # pacing — search engines throttle bursts
        for hit in web_search(q, limit=6):
            if not _relevant(hit, topic):
                continue
            if total >= target_chars or hit["url"] in have:
                continue
            have.add(hit["url"])
            url = hit["url"]
            if progress_cb:
                progress_cb(f"fetching: {hit['title'][:60]}")
            doc = None
            low = url.lower()
            if "slideshare.net" in low:
                doc = slideshare_transcript(url)
            elif low.endswith(".pdf") or "filetype=pdf" in low:
                doc = fetch_pdf_text(url)
            else:
                doc = fetch_page_text(url)
            if doc:
                corpus.append(doc)
                total += len(doc["text"])
    log.info("deck research: %d sources, %d chars for %r", len(corpus), total, topic)
    return corpus
