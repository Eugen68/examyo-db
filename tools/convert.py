#!/usr/bin/env python3
"""Convertește bazele de întrebări din Sim_exam_yo (YO6OWN) în JSON și CSV.

Rulare (din rădăcina repo-ului):
    python3 tools/convert.py

Citește fișierele db_* din submodulul `upstream/` și scrie:
    data/<slug>.json      o bază de date per fișier, cu metadate
    data/all.json         toate bazele într-un singur fișier
    data/csv/<slug>.csv   aceleași date, tabelar (UTF-8 cu BOM, se deschide corect în Excel)
    data/index.json       lista bazelor + versiunea upstream din care s-au generat
    images/               figurile folosite de întrebări și de rezolvări

Ieșirea nu conține timestamp-uri, ca o regenerare fără modificări upstream să nu producă diff.
"""

import csv
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = ROOT / "upstream"
SHELF = UPSTREAM / "html" / "shelf"
DATA = ROOT / "data"
IMAGES = ROOT / "images"

# Ce fișier din upstream, ce slug, ce categorie și pentru ce clase.
# Maparea pe clase e cea folosită de sim_gen1..4.cgi din upstream.
# db_legis2 și db_op2 sunt doar placeholdere (o singură întrebare, nefolosite) și sunt omise.
DATABASES = [
    ("db_tech1", "radiotehnica-clasa-1", "radiotehnica", ["I"]),
    ("db_tech2", "radiotehnica-clasa-2", "radiotehnica", ["II"]),
    ("db_tech3", "radiotehnica-clasa-3", "radiotehnica", ["III"]),
    ("db_legis1", "legislatie-clasa-1-2", "legislatie", ["I", "II"]),
    ("db_legis3", "legislatie-clasa-3", "legislatie", ["III"]),
    ("db_legis4", "legislatie-clasa-4", "legislatie", ["IV"]),
    ("db_sanctiuni", "sanctiuni", "sanctiuni", ["I", "II", "III", "IV"]),
    ("db_op1", "operare-clasa-1-2", "operare", ["I", "II"]),
    ("db_op3", "operare-clasa-3", "operare", ["III"]),
    ("db_op4", "operare-clasa-4", "operare", ["IV"]),
    ("db_ntsm", "ntsm-clasa-1-3", "protectia-muncii", ["I", "II", "III"]),
    ("db_ntsm4", "ntsm-clasa-4", "protectia-muncii", ["IV"]),
]

# Câmpurile unei înregistrări, în ordinea din fișier (vezi sim_ver1.cgi din upstream).
F_ANSWER, F_QUESTION, F_IMAGE, F_A, F_B, F_C, F_D, F_CONTRIB, F_SOL_IMAGE, F_SOLUTION, F_SOL_AUTHOR = range(11)
LETTERS = "abcd"

# ---------------------------------------------------------------- HTML -> text

SUB = dict(zip("0123456789+-=()aehijklmnoprstuvx", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₕᵢⱼₖₗₘₙₒₚᵣₛₜᵤᵥₓ"))
SUP = dict(zip("0123456789+-=()in", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁱⁿ"))


def _script(text, table, marker):
    """Indice/exponent: Unicode când se poate, altfel _x / ^(xy)."""
    if text and all(ch in table for ch in text):
        return "".join(table[ch] for ch in text)
    return f"{marker}{text}" if len(text) == 1 else f"{marker}({text})"


def html_to_text(s):
    if not s:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"<li[^>]*>", "\n• ", s, flags=re.I)
    s = re.sub(r"</(?:ul|ol|table|p|div)>", "\n", s, flags=re.I)
    s = re.sub(r"</tr>", "\n", s, flags=re.I)
    s = re.sub(r"</t[dh]>", " | ", s, flags=re.I)

    def link(m):
        url, label = m.group(1).strip(), html_to_text(m.group(2)).strip()
        return label if not label or label == url else f"{label} ({url})"

    s = re.sub(r"<a\s[^>]*href\s*=\s*[\"']?([^\"'>\s]+)[^>]*>(.*?)</a>", link, s, flags=re.I | re.S)
    s = re.sub(r"<sub>(.*?)</sub>", lambda m: _script(html.unescape(m.group(1)), SUB, "_"), s, flags=re.I | re.S)
    s = re.sub(r"<sup>(.*?)</sup>", lambda m: _script(html.unescape(m.group(1)), SUP, "^"), s, flags=re.I | re.S)
    s = re.sub(r"<strike>(.*?)</strike>", lambda m: "~~" + m.group(1) + "~~", s, flags=re.I | re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    lines = [re.sub(r"[ \t]+", " ", ln).strip().rstrip("|").strip() for ln in s.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


# ---------------------------------------------------------------- parsing


def clean(v):
    v = (v or "").strip()
    return "" if v == "null" else v


def parse_image(field, used):
    """'fig_177.jpg 177' -> {'file': 'images/fig_177.jpg', 'width': 177}; 'null' -> None."""
    field = clean(field)
    if not field:
        return None
    parts = field.split()
    used.add(parts[0])
    width = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
    return {"file": f"images/{parts[0]}", "width": width}


def parse_header(line):
    hidden = re.search(r"<curricula>(.*?)</curricula>", line)
    title = html_to_text(re.sub(r"<font[^>]*>.*?</font>", "", line))
    title = re.split(r"\s+versiunea?\s+actualizat", title, flags=re.I)[0].strip(" ,-")
    version = re.search(r"v(?:ersiunea)?\.?\s*(\d+(?:\.\d+)+)", title, flags=re.I)
    return title, (version.group(1) if version else None), (hidden.group(1) if hidden else None)


def parse_db(path, slug, used_images):
    text = path.read_text(encoding="utf-8")
    head, *chunks = re.split(r"^##(\d+)#[ \t]*\r?$", text, flags=re.M)
    head_lines = head.strip().splitlines()
    title, version, curriculum = parse_header(head_lines[0])
    declared = int(head_lines[1]) if len(head_lines) > 1 and head_lines[1].strip().isdigit() else None

    questions = []
    for num, body in zip(chunks[0::2], chunks[1::2]):
        f = body.strip("\r\n").split("\n")
        f = [x.rstrip("\r") for x in f] + [""] * (11 - len(f))
        code, _, q_html = f[F_QUESTION].partition("~&") if "~&" in f[F_QUESTION] else ("", "", f[F_QUESTION])
        correct = f[F_ANSWER].strip().lower()
        if correct not in LETTERS:
            sys.exit(f"{path.name} #{num}: răspuns corect invalid {correct!r}")
        answers_html = [f[i].strip() for i in (F_A, F_B, F_C, F_D)]
        sol_html = clean(f[F_SOLUTION])
        questions.append({
            "id": f"{slug}/{num}",
            "number": int(num),
            "code": code.strip() or None,
            "question": html_to_text(q_html),
            "image": parse_image(f[F_IMAGE], used_images),
            "answers": [html_to_text(a) for a in answers_html],
            "correct": correct,
            "correct_index": LETTERS.index(correct),
            "contributor": html_to_text(clean(f[F_CONTRIB])) or None,
            "explanation": html_to_text(sol_html) or None,
            "explanation_image": parse_image(f[F_SOL_IMAGE], used_images),
            "explanation_author": html_to_text(clean(f[F_SOL_AUTHOR])) or None,
            "html": {
                "question": q_html.strip(),
                "answers": answers_html,
                "explanation": sol_html or None,
            },
        })
    return {
        "title": title,
        "version": version,
        "curriculum": curriculum,
        "declared_count": declared,
        "count": len(questions),
        "with_explanation": sum(1 for q in questions if q["explanation"]),
    }, questions


# ---------------------------------------------------------------- output

CSV_COLUMNS = ["id", "code", "question", "image", "a", "b", "c", "d", "correct",
               "explanation", "explanation_image", "contributor", "explanation_author"]


def write_json(path, obj, compact=False):
    opts = {"separators": (",", ":")} if compact else {"indent": 1}
    path.write_text(json.dumps(obj, ensure_ascii=False, **opts) + "\n", encoding="utf-8")


def write_csv(path, questions):
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_COLUMNS)
        for q in questions:
            w.writerow([
                q["id"], q["code"] or "", q["question"], (q["image"] or {}).get("file", ""),
                *q["answers"], q["correct"], q["explanation"] or "",
                (q["explanation_image"] or {}).get("file", ""),
                q["contributor"] or "", q["explanation_author"] or "",
            ])


def upstream_commit():
    try:
        return subprocess.check_output(["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return None


def main():
    if not (UPSTREAM / "db_tech1").exists():
        sys.exit("Lipsește submodulul. Rulează: git submodule update --init")

    for d in (DATA, DATA / "csv", IMAGES):
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)

    used_images, index, combined = set(), [], []
    for fname, slug, category, classes in DATABASES:
        meta, questions = parse_db(UPSTREAM / fname, slug, used_images)
        meta = {"slug": slug, "source_file": fname, "category": category, "classes": classes, **meta}
        write_json(DATA / f"{slug}.json", {**meta, "questions": questions})
        write_csv(DATA / "csv" / f"{slug}.csv", questions)
        index.append(meta)
        combined.append({**meta, "questions": questions})
        print(f"{slug:24} {meta['count']:4} întrebări, {meta['with_explanation']:4} cu explicație")

    missing = []
    for name in sorted(used_images):
        src = SHELF / name
        if src.exists():
            shutil.copy2(src, IMAGES / name)
        else:
            missing.append(name)

    source = {
        "upstream": "https://github.com/6oskarwN/Sim_exam_yo",
        "upstream_commit": upstream_commit(),
        "author": "Francisc Toth, YO6OWN",
        "website": "http://examyo.scienceontheweb.net",
        "license": "GPL-2.0-or-later",
    }
    write_json(DATA / "index.json", {"source": source, "databases": index, "missing_images": missing})
    write_json(DATA / "all.json", {"source": source, "databases": combined}, compact=True)

    total = sum(m["count"] for m in index)
    expl = sum(m["with_explanation"] for m in index)
    print(f"\nTotal: {total} întrebări, {expl} cu explicație, {len(used_images)} imagini"
          + (f", {len(missing)} lipsă: {', '.join(missing)}" if missing else ""))


if __name__ == "__main__":
    main()
