"""Title, description and tags of a Veritas Recruitment Agency upload, from its job file.

usage: python3 veritas/describe.py veritas/jobs/vraNNN.json  -> JSON {yt_title, description, tags}
The description carries the full job details and the employer's own application link, ahead of everything else.
YouTube limits: title 100 characters, description 5,000.
"""
import sys, json

JOB = json.load(open(sys.argv[1])); J, X = JOB["job"], JOB["details"]
short = JOB["format"] == "short"
bul = lambda xs: "\n".join(f"• {x}" for x in xs)
parts = [
    f"{J['employer']} is hiring: {J['title']} in {J['location']}",
    "",
    f"✅ Apply directly on {J['employer']}'s careers site: {J['apply_url']}",
    "",
    f"💵 Pay: {J['pay_full']}",
    f"🏢 Employer: {J['employer']}",
    f"📍 Location: {J['location']}" + (f" ({J['workplace']})" if J.get("workplace") else ""),
    f"🕒 Type: {J.get('type', 'Full time')}",
    f"🗓 Posted: {J['posted']}" + (f"  ·  Job ID: {J['ref']}" if J.get("ref") else ""),
    "",
    "ABOUT THE ROLE",
    X["about"],
    "",
    "WHAT YOU'LL DO",
    bul(X["duties"]),
    "",
    "WHAT YOU NEED",
    bul(X["needs"]),
]
if X.get("nice"): parts += ["", "NICE TO HAVE", bul(X["nice"])]
parts += ["", "PAY & BENEFITS", X["benefits"]]
if X.get("notes"): parts += ["", "GOOD TO KNOW", bul(X["notes"])]
parts += [
    "",
    f"👉 How to apply: use the official link above ({J['apply_url']}). Details are summarised from {J['employer']}'s posting "
    f"on {J['apply_site']}; the posting there is the final word on the role.",
    "",
    f"Veritas Recruitment Agency shares open US tech roles published on employers' own careers sites. We are not "
    f"{J['employer']} and are not affiliated with it. We never charge candidates and never ask for payment or bank details.",
    "",
    "🔔 Subscribe for new US tech jobs every day.",
    "",
    " ".join(JOB["hashtags"] + (["#shorts"] if short else [])),
]
desc = "\n".join(parts)
title = JOB["yt_title"] + (" #shorts" if short and "#shorts" not in JOB["yt_title"] else "")
assert len(title) <= 100, f"title too long ({len(title)})"
assert len(desc) <= 5000, f"description too long ({len(desc)})"
assert "newsflix" not in (desc + title + " ".join(JOB["tags"])).lower(), "never name the source site"
print(json.dumps({"yt_title": title, "description": desc, "tags": JOB["tags"]}, ensure_ascii=False, indent=1))
