"""Fetch the full text of each queued job posting from the employer's own careers site (runs in GitHub Actions).

usage: python3 veritas/fetch.py veritas/queue/YYYY-MM-DD.json
Writes veritas/fetched/YYYY-MM-DD/<safe id>.json: {source_id, url, http, ok, text}. The text is the posting as the
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
