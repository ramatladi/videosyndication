"""Fetch the full text of each queued job posting from the employer's own careers site (runs in GitHub Actions).

usage: python3 veritas/fetch.py veritas/queue/YYYY-MM-DD.json
Writes veritas/fetched/YYYY-MM-DD/<safe id>.json: {source_id, url, http, ok, text}, and for the queue's "logos" entries
every logo candidate the employer's own pages name (veritas/fetched/YYYY-MM-DD/logos/<slug>/NN.ext + index.json). The text is the posting as the
employer publishes it (Workday and Greenhouse through their public job APIs, everything else from the page itself:
its schema.org JobPosting when it has one, else its visible text). Standard library only; one request at a time.
"""
import sys, os, json, re, time, html, urllib.request, urllib.parse

UA = "Mozilla/5.0 (compatible; VeritasRecruitment/1.0; +https://github.com/ramatladi/videosyndication)"
Q = json.load(open(sys.argv[1]))
DAY = os.path.splitext(os.path.basename(sys.argv[1]))[0]
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[1]))), "fetched", DAY)
os.makedirs(OUT, exist_ok=True)

def get(url, accept="text/html,application/json"):
    req = urllib.request.Request(url, headers={"user-agent": UA, "accept": accept, "accept-language": "en-US"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.status, r.read().decode("utf-8", "replace")

def text_of(markup):
    markup = re.sub(r"(?is)<(script|style|noscript|svg|nav|footer|header)\b.*?</\1>", " ", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</(p|li|h[1-6]|div|tr|ul|ol)>", "\n", markup)
    markup = re.sub(r"(?i)<li[^>]*>", "\n• ", markup)
    t = html.unescape(re.sub(r"<[^>]+>", " ", markup))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()

def jobposting(page):
    for m in re.finditer(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page):
        try: data = json.loads(m.group(1).strip())
        except Exception: continue
        for d in (data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []):
            if isinstance(d, dict) and d.get("@type") == "JobPosting" and d.get("description"):
                extra = {k: d.get(k) for k in ("title", "datePosted", "validThrough", "employmentType", "baseSalary", "jobLocation", "jobLocationType") if d.get(k)}
                return text_of(html.unescape(d["description"])) + "\n\n[posting fields] " + json.dumps(extra, ensure_ascii=False)
    return None

def fetch(job):
    url = job["url"]; u = urllib.parse.urlparse(url)
    if u.scheme != "https": raise ValueError("https only")
    m = re.match(r"^([a-z0-9-]+)\.wd\d+\.myworkdayjobs\.com$", u.hostname or "")
    if m:  # Workday: the public job API behind the page
        parts = [p for p in u.path.split("/") if p]
        site, rest = (parts[1], parts[2:]) if re.fullmatch(r"[a-z]{2}-[A-Z]{2}", parts[0]) else (parts[0], parts[1:])
        st, body = get(f"https://{u.hostname}/wday/cxs/{m.group(1)}/{site}/" + "/".join(rest), "application/json")
        j = json.loads(body)["jobPostingInfo"]
        head = f"{j.get('title')}\nLocation: {j.get('location')} {j.get('additionalLocations') or ''}\nTime type: {j.get('timeType')}\nPosted: {j.get('postedOn')}\nReq: {j.get('jobReqId')}\n\n"
        return st, head + text_of(j.get("jobDescription", ""))
    gh = urllib.parse.parse_qs(u.query).get("gh_jid")
    if gh and job.get("src"):  # Greenhouse job on the company's own site: the board's public API
        st, body = get(f"https://boards-api.greenhouse.io/v1/boards/{job['src']}/jobs/{gh[0]}", "application/json")
        j = json.loads(body)
        return st, f"{j.get('title')}\nLocation: {(j.get('location') or {}).get('name')}\n\n" + text_of(html.unescape(j.get("content", "")))
    st, page = get(url)
    return st, jobposting(page) or text_of(page)

LOGO_HINT = re.compile(r"logo|brand|wordmark", re.I)

def absolute(base, src):
    return urllib.parse.urljoin(base, html.unescape(src.strip()))

def download(url, path, limit=3_000_000):
    req = urllib.request.Request(url, headers={"user-agent": UA, "accept": "image/svg+xml,image/png,image/webp,image/*"})
    with urllib.request.urlopen(req, timeout=45) as r:
        body = r.read(limit + 1)
    if len(body) > limit or len(body) < 100: raise ValueError(f"size {len(body)}")
    open(path, "wb").write(body)
    return r.headers.get("content-type", "")

def logo_candidates(page_url, page):
    """Where an employer's own page names its logo: schema.org Organization logo, og:logo, <img> marked as the logo,
    inline <svg> marked as the logo, and the site's SVG/touch icons."""
    found = []
    for m in re.finditer(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page):
        for u in re.findall(r'"logo"\s*:\s*(?:\{[^}]*?"url"\s*:\s*)?"([^"]+)"', m.group(1)):
            found.append(("jsonld", absolute(page_url, u)))
    for m in re.finditer(r'(?is)<meta[^>]+property=["\']og:logo["\'][^>]*content=["\']([^"\']+)', page):
        found.append(("og:logo", absolute(page_url, m.group(1))))
    for m in re.finditer(r'(?is)<img\b[^>]*>', page):
        tag = m.group(0); src = re.search(r'\bsrc=["\']([^"\']+)', tag)
        if src and LOGO_HINT.search(tag) and not src.group(1).startswith("data:"):
            found.append(("img", absolute(page_url, src.group(1))))
    for m in re.finditer(r'(?is)<svg\b.*?</svg>', page):
        svg, before = m.group(0), page[max(0, m.start() - 400): m.start()]
        if (LOGO_HINT.search(svg[:600]) or LOGO_HINT.search(before[-250:])) and len(svg) < 200_000:
            found.append(("inline-svg", svg))
    for m in re.finditer(r'(?is)<link\b[^>]*>', page):
        tag = m.group(0); href = re.search(r'\bhref=["\']([^"\']+)', tag)
        if href and re.search(r'rel=["\'][^"\']*(apple-touch-icon|mask-icon|icon)', tag, re.I) and (".svg" in href.group(1) or "apple-touch" in tag or "image/svg" in tag):
            found.append(("icon", absolute(page_url, href.group(1))))
    seen, out = set(), []
    for kind, v in found:
        if v not in seen: seen.add(v); out.append((kind, v))
    return out[:14]

def fetch_logos(entry):
    """entry {slug, employer, pages[]}: saves every logo candidate from the employer's own pages for review."""
    folder = os.path.join(OUT, "logos", re.sub(r"[^a-z0-9-]+", "-", entry["slug"].lower()))
    os.makedirs(folder, exist_ok=True); index = []
    for page_url in entry["pages"]:
        try:
            st, page = get(page_url)
        except Exception as e:
            index.append({"page": page_url, "error": f"{type(e).__name__}: {e}"[:200]}); continue
        for kind, v in logo_candidates(page_url, page):
            n = len([x for x in index if x.get("file")]) + 1
            item = {"page": page_url, "kind": kind}
            try:
                if kind == "inline-svg":
                    svg = v if "xmlns=" in v[:400] else v.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
                    path = os.path.join(folder, f"{n:02d}.svg"); open(path, "w").write(svg); item["source"] = page_url + " (inline SVG)"
                else:
                    ext = (re.search(r"\.(svg|png|webp|jpe?g|ico)(?:$|[?#])", v, re.I) or [None, "img"])[1].lower()
                    path = os.path.join(folder, f"{n:02d}.{ext}"); ctype = download(v, path); item.update(source=v, type=ctype)
                item["file"] = os.path.basename(path)
            except Exception as e:
                item.update(source=v[:300] if kind != "inline-svg" else page_url, error=f"{type(e).__name__}: {e}"[:200])
            index.append(item); time.sleep(0.5)
        time.sleep(2)
    json.dump({"employer": entry["employer"], "candidates": index}, open(os.path.join(folder, "index.json"), "w"), indent=1)
    print("logos", entry["slug"], len([x for x in index if x.get("file")]), "candidates")

for entry in Q.get("logos", []):
    try: fetch_logos(entry)
    except Exception as e: print("logos", entry.get("slug"), "failed", e)

for i, job in enumerate(Q["jobs"]):
    if i: time.sleep(2)
    out = {"source_id": job["source_id"], "url": job["url"], "ok": False, "http": None, "text": ""}
    try:
        st, txt = fetch(job)
        out.update(http=st, ok=st == 200 and len(txt) > 400, text=txt[:16000])
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"[:300]
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", job["source_id"])[:80]
    json.dump(out, open(os.path.join(OUT, name + ".json"), "w"), indent=1, ensure_ascii=False)
    print(job["source_id"], out["ok"], out["http"], len(out["text"]), out.get("error", ""))
