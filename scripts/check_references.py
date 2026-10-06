"""Verify every reference cited in the report against Crossref and fetch abstracts.

Input : report/src/references_input.json   (key, title, first-author surname, year, optional DOI)
Output: report/src/references.json          (authoritative metadata used to build the bibliography)
        report/reference_check.csv          (one row per reference: status and what was compared)
        report/src/abstracts.json           (abstracts used to check factual claims taken from papers)

Entries marked "manual": true (grey literature without a DOI) are copied as given and
flagged "manual - not in Crossref" in the check file.

Usage (from the repo root):  python scripts/check_references.py
"""
import csv
import difflib
import html
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "report" / "src"
UA = {"User-Agent": "spring-drying-thesis-reference-check/1.0 (python urllib)"}


def get_json(url, retries=3):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except Exception as e:  # network hiccup or 404
            if "404" in str(e):
                return None
            time.sleep(2 * (attempt + 1))
    return None


def norm(s):
    s = html.unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("-", " ")).split()


def similarity(a, b):
    return difflib.SequenceMatcher(None, " ".join(norm(a)), " ".join(norm(b))).ratio()


def year_of(m):
    for k in ("published-print", "published", "issued", "published-online"):
        parts = (m.get(k) or {}).get("date-parts")
        if parts and parts[0] and parts[0][0]:
            return int(parts[0][0])
    return None


def full_title(m):
    t = (m.get("title") or [""])[0]
    sub = (m.get("subtitle") or [""])
    return f"{t}: {sub[0]}" if sub and sub[0] and sub[0].lower() not in t.lower() else t


def crossref_by_doi(doi):
    d = get_json("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="/:()"))
    return d["message"] if d else None


def crossref_search(title, author):
    q = urllib.parse.urlencode({"query.bibliographic": title, "query.author": author, "rows": 5})
    d = get_json("https://api.crossref.org/works?" + q)
    if not d:
        return None, 0.0
    best, best_s = None, 0.0
    for item in d["message"]["items"]:
        s = similarity(title, full_title(item))
        if s > best_s:
            best, best_s = item, s
    return best, best_s


def abstract_of(m):
    if m.get("abstract"):
        return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", m["abstract"]))).strip()
    doi = m.get("DOI")
    if doi:
        d = get_json(f"https://api.semanticscholar.org/graph/v1/paper/DOI:{urllib.parse.quote(doi, safe='/')}?fields=abstract")
        time.sleep(1.2)
        if d and d.get("abstract"):
            return d["abstract"]
    return ""


def main():
    refs_in = json.loads((SRC / "references_input.json").read_text(encoding="utf-8-sig"))
    out, rows, abstracts = [], [], {}
    for ref in refs_in:
        key = ref["key"]
        if ref.get("manual"):
            ok = bool(ref.get("verified"))
            out.append({**ref, "verified": ok, "source": "manual"})
            rows.append({"key": key, "status": ("verified (manual): " if ok else "UNVERIFIED - not cited: ") + ref.get("verified_by", ""), "claimed_title": ref["title"],
                         "found_title": "", "title_similarity": "", "claimed_year": ref["year"], "found_year": "",
                         "first_author_match": "", "doi": ref.get("doi", ""), "container": ref.get("journal", "")})
            continue
        m, sim = None, 0.0
        if ref.get("doi"):
            m = crossref_by_doi(ref["doi"])
            sim = similarity(ref["title"], full_title(m)) if m else 0.0
        if m is None or sim < 0.8:
            cand, csim = crossref_search(ref["title"], ref["author"])
            if cand is not None and csim > sim:
                m, sim = cand, csim
        time.sleep(0.5)
        if m is None:
            rows.append({"key": key, "status": "NOT FOUND", "claimed_title": ref["title"], "found_title": "",
                         "title_similarity": 0, "claimed_year": ref["year"], "found_year": "",
                         "first_author_match": "", "doi": ref.get("doi", ""), "container": ""})
            out.append({**ref, "verified": False, "source": "not found"})
            continue
        authors = [f"{a.get('family', a.get('name', ''))}, {a.get('given', '')}".strip(", ")
                   for a in m.get("author", [])]
        first = (m.get("author") or [{}])[0]
        fam = first.get("family", first.get("name", ""))
        author_ok = norm(ref["author"])[:1] == norm(fam)[:1] if fam else False
        if ref.get("authors_override"):
            authors, author_ok = ref["authors_override"], True
        fy = year_of(m)
        status = "verified" if sim >= 0.9 and author_ok else ("check" if sim >= 0.75 else "MISMATCH")
        if status == "verified" and fy and abs(fy - ref["year"]) > 1:
            status = "check (year)"
        entry = {
            "key": key, "verified": status == "verified", "source": "crossref",
            "type": m.get("type"), "authors": authors, "title": html.unescape(full_title(m)),
            "journal": html.unescape((m.get("container-title") or [""])[0]), "volume": m.get("volume", ""),
            "issue": m.get("issue", ""), "pages": m.get("page", "") or m.get("article-number", ""),
            "year": fy or ref["year"], "doi": m.get("DOI", ""), "publisher": m.get("publisher", ""),
            "claimed_year": ref["year"],
        }
        out.append(entry)
        abstracts[key] = abstract_of(m)
        rows.append({"key": key, "status": status, "claimed_title": ref["title"], "found_title": entry["title"],
                     "title_similarity": round(sim, 3), "claimed_year": ref["year"], "found_year": fy,
                     "first_author_match": author_ok, "doi": entry["doi"], "container": entry["journal"]})
        print(f"{key:20s} {status:14s} sim={sim:.2f} {fy} {entry['journal'][:45]}")

    (SRC / "references.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    (SRC / "abstracts.json").write_text(json.dumps(abstracts, indent=2, ensure_ascii=False), encoding="utf-8")
    with open(ROOT / "report" / "reference_check.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
