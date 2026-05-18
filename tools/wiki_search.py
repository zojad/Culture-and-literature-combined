#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIKI = ROOT / "wiki"
WORD_RE = re.compile(r"[\wčšžćđČŠŽĆĐ]+", re.UNICODE)


@dataclass
class Hit:
    path: Path
    score: int
    title: str
    page_type: str
    bucket: str
    label: str
    excerpt: str


MAINTENANCE_NAMES = {"log.md", "open-questions.md", "contradictions.md"}
LITERATURE_HINTS = {
    "literature", "literary", "writer", "writers", "author", "authors", "work", "works",
    "representative", "representatives", "novel", "poem", "poetry", "drama", "play",
    "victorian", "renaissance", "romantic", "romanticism", "modernism", "realism",
    "naturalism", "postmodernism",
}
HISTORY_HINTS = {
    "history", "historical", "period", "periods", "anglo", "saxon", "anglo-saxon", "norman",
    "monarch", "monarchs", "king", "queen", "magna", "domesday", "empire", "commonwealth",
    "parliament", "church", "reformation", "victorian",
}
US_HINTS = {
    "declaration", "independence", "constitution", "congress", "president", "usa", "u.s.",
    "american", "america",
}


def terms(query: str) -> list[str]:
    return [t.lower() for t in WORD_RE.findall(query) if len(t) > 1]


def normalize_text(text: str) -> str:
    return " ".join(terms(text))


def infer_query_intent(query: str) -> dict[str, bool]:
    qterms = set(terms(query))
    return {
        "literature": bool(qterms & LITERATURE_HINTS),
        "history": bool(qterms & HISTORY_HINTS),
        "us": bool(qterms & US_HINTS),
        "representatives": bool(qterms & {"writer", "writers", "author", "authors", "representative", "representatives", "works"}),
        "direct_fact": bool(qterms & {"when", "who", "what"}),
    }


def read_title(text: str, fallback: str) -> str:
    # Prefer frontmatter title, then first markdown H1, then filename.
    m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', text, re.M)
    if m:
        return m.group(1).strip()
    m = re.search(r'^#\s+(.+?)\s*$', text, re.M)
    if m:
        return m.group(1).strip()
    return fallback


def split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if not m:
        return "", text
    return m.group(1), text[m.end():]


def read_frontmatter_value(frontmatter: str, key: str) -> str | None:
    m = re.search(rf"^{re.escape(key)}:\s*[\"']?(.+?)[\"']?\s*$", frontmatter, re.M)
    return m.group(1).strip() if m else None


def classify_hit(path: Path, frontmatter: str) -> tuple[str, str]:
    rel = path.relative_to(ROOT)
    page_type = (read_frontmatter_value(frontmatter, "type") or "").strip().lower()
    name = path.name.lower()
    rel_str = str(rel).lower()

    if name in MAINTENANCE_NAMES or "/maintenance/" in rel_str or page_type in {"maintenance", "log"}:
        return "Maintenance", "maintenance"
    if name in {"readme.md", "index.md"} or page_type == "index":
        return "Navigation", "navigation"
    if "/questions/models/" in rel_str:
        return "Model answer", "model"
    if "/themes/" in rel_str:
        return "Theme", "direct"
    if "/history/" in rel_str or "/literature/" in rel_str:
        return "Topic page", "direct"
    if "/timelines/" in rel_str:
        return "Timeline", "support"
    if "glossary" in rel_str:
        return "Glossary", "support"
    if page_type == "concept":
        return "Reference", "support"
    if page_type == "question":
        return "Question page", "model"
    return "Reference", "support"


def classify_domain(path: Path, frontmatter: str) -> str:
    rel = str(path.relative_to(ROOT)).lower()
    source_text = (read_frontmatter_value(frontmatter, "sources") or "").lower()
    title_text = (read_frontmatter_value(frontmatter, "title") or "").lower()
    hay = " ".join([rel, source_text, title_text])
    if any(key in hay for key in ["brit_literature", "us_literature", "/literature/", "writers", "works"]):
        return "literature"
    if any(key in hay for key in ["brit_culture", "us_culture", "/history/", "/themes/", "constitution", "parliament"]):
        return "history"
    return "general"


def section_lines(body: str, heading: str) -> list[str]:
    lines = body.splitlines()
    in_section = False
    collected: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            normalized = stripped.lstrip("#").strip().lower()
            if in_section and normalized != heading.lower():
                break
            in_section = normalized == heading.lower()
            continue
        if in_section and stripped:
            collected.append(stripped)
    return collected


def clean_summary_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        if line.startswith("#"):
            continue
        if re.fullmatch(r"[-*]\s*", line):
            continue
        if line.lower().startswith(("source:", "sources:", "path:", "related:")):
            continue
        if line.startswith("`data/") or line.startswith("`British ") or line.startswith("`American "):
            continue
        if re.fullmatch(r"`[^`]+\.md`\.?", line):
            continue
        compact = re.sub(r"\s+", " ", line)
        cleaned.append(compact)
    return cleaned


def summarize_match(body: str, ts: list[str], width: int = 220) -> str:
    prioritized = (
        section_lines(body, "Exam answer frame")
        + section_lines(body, "Question")
        + section_lines(body, "Thesis")
    )
    cleaned = clean_summary_lines(prioritized)
    if not cleaned:
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        cleaned = clean_summary_lines(lines)

    if not cleaned:
        return ""

    scored: list[tuple[int, str]] = []
    for line in cleaned:
        lower = line.lower()
        score = sum(lower.count(t) for t in ts)
        if score:
            scored.append((score, line))

    text = max(scored, key=lambda item: (item[0], -cleaned.index(item[1])))[1] if scored else cleaned[0]
    text = re.sub(r"^[-*]\s*", "", text)
    if len(text) > width:
        text = text[: width - 4].rstrip() + " ..."
    return text


def score_label(score: int) -> str:
    if score >= 20:
        return "Best match"
    if score >= 10:
        return "Strong match"
    return "Related"


def title_match_bonus(query: str, title: str, path: Path) -> int:
    qnorm = normalize_text(query)
    tnorm = normalize_text(title)
    pnorm = normalize_text(path.stem.replace("-", " "))
    if not qnorm:
        return 0

    bonus = 0
    if qnorm == tnorm or qnorm == pnorm:
        bonus += 30
    elif qnorm in tnorm or qnorm in pnorm:
        bonus += 20

    qterms = set(qnorm.split())
    tterms = set(tnorm.split())
    pterms = set(pnorm.split())
    if qterms and qterms.issubset(tterms):
        bonus += 12
    elif qterms and qterms.issubset(pterms):
        bonus += 8

    if title.lower().startswith(query.lower()):
        bonus += 8
    return bonus


def adjusted_score(score: int, query: str, title: str, path: Path, frontmatter: str) -> int:
    rel = str(path.relative_to(ROOT)).lower()
    name = path.name.lower()
    page_type = (read_frontmatter_value(frontmatter, "type") or "").strip().lower()
    intent = infer_query_intent(query)
    page_domain = classify_domain(path, frontmatter)
    if name in MAINTENANCE_NAMES or "/maintenance/" in rel or page_type in {"maintenance", "log"}:
        score -= 100
    if name in {"readme.md", "index.md"} or page_type == "index":
        score -= 8
    if "/questions/models/" in rel:
        score += 3
    if "/themes/" in rel:
        score += 5
    if "/history/" in rel or "/literature/" in rel:
        score += 2
    if "/timelines/" in rel:
        score += 1
    score += title_match_bonus(query, title, path)

    # Intent-aware ranking
    if intent["literature"]:
        if page_domain == "literature":
            score += 10
        elif page_domain == "history":
            score -= 4
        if "/questions/models/model-05" in rel or "/questions/models/model-06" in rel:
            score += 10
        if "/themes/victorian-values.md" in rel and intent["representatives"]:
            score -= 8

    if intent["history"] and not intent["literature"]:
        if page_domain == "history":
            score += 6
        elif page_domain == "literature":
            score -= 2

    if intent["representatives"]:
        if "/literature/" in rel:
            score += 10
        if "/questions/models/model-05" in rel:
            score += 12
        if "/questions/models/model-06" in rel and "modernism" in query.lower():
            score += 8
        if "/themes/" in rel and "writers" not in title.lower() and "works" not in title.lower():
            score -= 6

    if intent["us"]:
        if "declaration-of-independence" in rel:
            score += 12
        if "constitution" in rel or "us-" in rel:
            score += 3
        if "british-empire" in rel or "anglican-church" in rel or "victorian-values" in rel:
            score -= 5

    if "magna carta" in query.lower() or "domesday" in query.lower():
        if "magna-carta-and-domesday-book" in rel or "model-03" in rel:
            score += 12

    if "commonwealth" in query.lower() or "british empire" in query.lower():
        if "british-empire-and-commonwealth" in rel or "model-01" in rel:
            score += 12

    return score


def make_excerpt(body: str, ts: list[str], width: int = 360) -> str:
    lower = body.lower()
    pos = -1
    for t in ts:
        pos = lower.find(t)
        if pos >= 0:
            break
    if pos < 0:
        pos = 0
    start = max(0, pos - width // 3)
    end = min(len(body), start + width)
    out = re.sub(r"\s+", " ", body[start:end]).strip()
    if start > 0:
        out = "... " + out
    if end < len(body):
        out += " ..."
    return out


def search(query: str, limit: int = 10, include_navigation: bool = False) -> list[Hit]:
    ts = terms(query)
    if not ts:
        return []
    hits: list[Hit] = []
    for path in WIKI.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        frontmatter, body = split_frontmatter(text)
        lower = text.lower()
        score = 0
        for t in ts:
            c = lower.count(t)
            score += c * (3 if t in path.stem.lower() else 1)
        if score:
            page_type, bucket = classify_hit(path, frontmatter)
            if bucket == "maintenance":
                continue
            if bucket == "navigation" and not include_navigation:
                continue
            title = read_title(text, path.stem)
            adj_score = adjusted_score(score, query, title, path, frontmatter)
            summary = summarize_match(body, ts) or make_excerpt(body, ts)
            hits.append(
                Hit(
                    path=path,
                    score=adj_score,
                    title=title,
                    page_type=page_type,
                    bucket=bucket,
                    label=score_label(adj_score),
                    excerpt=summary,
                )
            )
    bucket_order = {"direct": 0, "model": 1, "support": 2, "navigation": 3, "maintenance": 4}
    hits.sort(key=lambda h: (bucket_order.get(h.bucket, 9), -h.score, str(h.path)))
    return hits[:limit]


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the persistent LLM Wiki markdown pages.")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--include-navigation", action="store_true")
    args = parser.parse_args()
    hits = search(args.query, args.limit, include_navigation=args.include_navigation)
    if not hits:
        print("No wiki matches found. Search the source corpus with tools/search.py next.")
        return
    sections = [
        ("Best direct answer pages", "direct"),
        ("Model answers", "model"),
        ("Supporting reference pages", "support"),
    ]
    if args.include_navigation:
        sections.append(("Navigation pages", "navigation"))
    index = 1
    for heading, bucket in sections:
        section_hits = [hit for hit in hits if hit.bucket == bucket]
        if not section_hits:
            continue
        print(heading)
        print()
        for hit in section_hits:
            rel = hit.path.relative_to(ROOT)
            print(f"{index}. {hit.title}")
            print(f"   Type: {hit.page_type} | Match: {hit.label}")
            print(f"   Path: {rel}")
            print(f"   Summary: {hit.excerpt}")
            print()
            index += 1


if __name__ == "__main__":
    main()
