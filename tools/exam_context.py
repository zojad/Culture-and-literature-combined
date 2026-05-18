#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "index" / "search.sqlite"

STOP = {
    "the", "and", "for", "with", "from", "that", "this", "into", "about", "what", "when", "who",
    "how", "why", "are", "was", "were", "does", "did", "have", "has", "had", "your", "their",
    "comment", "explain", "present", "name", "discuss", "significance", "major", "period", "periods",
}

EXAM_HINTS = {
    "empire": ["colonies", "commonwealth", "decolonization", "imperial", "realm"],
    "commonwealth": ["british empire", "member states", "postcolonial", "realm"],
    "magna": ["magna carta", "king john", "charter", "liberties"],
    "domesday": ["domesday book", "norman", "william", "survey"],
    "anglo-saxon": ["anglo saxon", "early england", "monarch", "king"],
    "norman": ["norman conquest", "william", "monarchy"],
    "victorian": ["nineteenth century", "queen victoria", "industrial"],
    "modernism": ["modernist", "eliot", "pound", "stein"],
    "romanticism": ["romantic", "transcendentalism"],
    "realism": ["realist", "naturalism"],
}

LOW_VALUE_TITLES = {"index", "contents", "further reading", "exercises"}

# Heuristics for likely commentary/news-style files that are less stable for exam core facts.
COMMENTARY_NAME_HINTS = {
    "what about",
    "opened my eyes",
    "lingers",
    "urged to",
    "trip",
    "my ",
    "opinion",
    "guardian",
}

# Heuristics for textbook/lecture-style anchors that are usually better for baseline exam facts.
TEXTBOOK_NAME_HINTS = {
    "civilization",
    "outline",
    "lectures",
    "zapiski",
    "berilo",
    "constitution",
}

DOMAIN_SOURCE = {
    "history": {"brit_culture", "us_culture"},
    "literature": {"brit_literature", "us_literature"},
    "politics": {"brit_culture", "us_culture"},
}

LIT_TERMS = {
    "literature", "author", "writers", "writer", "novel", "poetry", "poem", "drama", "modernism",
    "romanticism", "realism", "naturalism", "postmodernism", "lost", "generation", "work", "works",
}

HIST_TERMS = {
    "empire", "commonwealth", "magna", "domesday", "anglo", "norman", "victorian", "parliament",
    "monarch", "king", "queen", "civil", "war", "restoration", "protectorate", "history",
}


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[\w'-]+", text) if len(t) > 2]


def build_query(question: str) -> str:
    toks = [t for t in tokenize(question) if t not in STOP]
    expanded = set(toks)
    qlow = question.lower()
    for key, extra in EXAM_HINTS.items():
        if key in qlow:
            expanded.update(extra)
    if not expanded:
        expanded = set(tokenize(question))
    parts = sorted(expanded)
    return " OR ".join(parts[:24]) if parts else '""'


def infer_domain(question: str) -> str | None:
    toks = set(tokenize(question))
    lit_score = len(toks & LIT_TERMS)
    hist_score = len(toks & HIST_TERMS)
    if lit_score >= hist_score + 1 and lit_score > 0:
        return "literature"
    if hist_score > 0:
        return "history"
    return None


def table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    row = cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
    return row is not None


def title_is_low_value(title: str) -> bool:
    t = title.strip().lower()
    if t in LOW_VALUE_TITLES:
        return True
    return t.startswith("index") or t.startswith("exercise") or t.startswith("contents")


def boosted_score(row: sqlite3.Row, question: str, domain: str | None) -> float:
    # bm25 lower is better; subtract boosts to rank earlier.
    score = float(row["rank"]) if row["rank"] is not None else 100.0
    qlow = question.lower()
    section = (row["section_title"] or "").lower()
    text = (row["text"] or "").lower()
    sid = row["source_id"]
    path_name = Path(row["path"]).name.lower()

    # Penalize low-value sections by default.
    if title_is_low_value(section):
        score += 2.0

    # Domain-aware boosts.
    if domain and sid in DOMAIN_SOURCE.get(domain, set()):
        score -= 1.2

    # If literature-ish query, favor literature sources heavily.
    if infer_domain(question) == "literature" and sid in {"us_literature", "brit_literature"}:
        score -= 1.8
    if infer_domain(question) == "literature" and sid in {"us_culture", "brit_culture"}:
        score += 0.8

    # Exact phrase/title proximity boosts.
    for phrase in ["magna carta", "domesday book", "british empire", "commonwealth", "house of commons", "house of lords", "modernism", "lost generation"]:
        if phrase in qlow and phrase in section:
            score -= 1.2
        elif phrase in qlow and phrase in text[:1000]:
            score -= 0.4

    # In history mode, prefer textbook/lecture sources and demote likely commentary/news pieces.
    if domain == "history":
        if any(h in path_name for h in COMMENTARY_NAME_HINTS):
            score += 1.4
        if any(h in path_name for h in TEXTBOOK_NAME_HINTS):
            score -= 0.8

    return score


def run_query(
    question: str,
    limit: int,
    source: str | None,
    exclude_worksheets: bool,
    exclude_low_value: bool,
    domain: str | None,
) -> list[sqlite3.Row]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    fts_q = build_query(question)

    if table_exists(cur, "chunks_fts"):
        where = ["chunks_fts MATCH ?"]
        params: list[object] = [fts_q]
        if source:
            where.append("c.source_id = ?")
            params.append(source)
        if exclude_worksheets:
            where.append("c.section_kind != 'worksheet'")
        if exclude_low_value:
            where.append("LOWER(c.section_title) NOT IN ('index', 'contents', 'further reading', 'exercises')")
            where.append("LOWER(c.section_title) NOT LIKE 'index %'")
            where.append("LOWER(c.section_title) NOT LIKE 'contents %'")
            where.append("LOWER(c.section_title) NOT LIKE 'exercise%'")
        if domain and not source:
            allowed = sorted(DOMAIN_SOURCE.get(domain, set()))
            if allowed:
                ph = ",".join("?" for _ in allowed)
                where.append(f"c.source_id IN ({ph})")
                params.extend(allowed)

        sql = f"""
            SELECT c.id, c.source_id, c.short_title, c.source_kind, c.page_number, c.path,
                   c.section_title, c.section_kind, c.quality_flags, c.text,
                   snippet(chunks_fts, 0, '[', ']', ' ... ', 16) AS snippet,
                   bm25(chunks_fts) AS rank
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            WHERE {' AND '.join(where)}
            ORDER BY rank
            LIMIT ?
        """
        params.append(max(limit * 5, 25))
        rows = cur.execute(sql, params).fetchall()
    else:
        where = ["pages_fts MATCH ?"]
        params = [fts_q]
        if source:
            where.append("p.source_id = ?")
            params.append(source)
        if domain and not source:
            allowed = sorted(DOMAIN_SOURCE.get(domain, set()))
            if allowed:
                ph = ",".join("?" for _ in allowed)
                where.append(f"p.source_id IN ({ph})")
                params.extend(allowed)
        sql = f"""
            SELECT p.id, p.source_id, p.short_title, p.source_kind, p.page_number, p.path,
                   '' as section_title, '' as section_kind, p.quality_flags, p.text,
                   snippet(pages_fts, 0, '[', ']', ' ... ', 16) AS snippet,
                   bm25(pages_fts) AS rank
            FROM pages_fts
            JOIN pages p ON p.id = pages_fts.rowid
            WHERE {' AND '.join(where)}
            ORDER BY rank
            LIMIT ?
        """
        params.append(max(limit * 5, 25))
        rows = cur.execute(sql, params).fetchall()

    conn.close()

    # Dedup by path+section and rerank with boosts.
    dedup: dict[tuple[str, str], sqlite3.Row] = {}
    for r in rows:
        key = (r["path"], r["section_title"])
        if key not in dedup:
            dedup[key] = r

    ranked = sorted(dedup.values(), key=lambda r: boosted_score(r, question, domain))
    return ranked[:limit]


def split_paragraphs(text: str) -> list[str]:
    blocks = []
    for part in re.split(r"\n\s*\n", text):
        cleaned = re.sub(r"\s+", " ", part).strip()
        if cleaned:
            blocks.append(cleaned)
    if not blocks:
        return []

    paragraphs = [blocks[0]]
    for block in blocks[1:]:
        prev = paragraphs[-1]
        should_merge = (
            len(prev) < 220
            or len(block) < 140
            or not re.search(r'[.!?:"\'](?:\s|\Z)', prev)
        )
        if should_merge:
            paragraphs[-1] = f"{prev} {block}"
        else:
            paragraphs.append(block)
    return paragraphs


def _match_position(text: str, query: str) -> int:
    tokens = [t.lower() for t in tokenize(query) if t not in STOP][:8]
    lower = text.lower()
    for tok in tokens:
        p = lower.find(tok)
        if p >= 0:
            return p
    return 0


def excerpt_paragraphs(text: str, query: str, width: int = 850) -> list[str]:
    paragraphs = split_paragraphs(text)
    if not paragraphs:
        return []

    best_idx = 0
    best_pos = None
    for idx, paragraph in enumerate(paragraphs):
        pos = _match_position(paragraph, query)
        if pos > 0 or query.lower() in paragraph.lower():
            if best_pos is None or pos < best_pos:
                best_idx = idx
                best_pos = pos

    selected = [paragraphs[best_idx]]
    total_len = len(selected[0])

    next_idx = best_idx + 1
    while next_idx < len(paragraphs) and total_len + len(paragraphs[next_idx]) <= width:
        selected.append(paragraphs[next_idx])
        total_len += len(paragraphs[next_idx])
        next_idx += 1

    if len(selected) == 1 and best_idx > 0 and total_len + len(paragraphs[best_idx - 1]) <= width:
        selected.insert(0, paragraphs[best_idx - 1])

    if best_idx > 0:
        selected[0] = "... " + selected[0]
    if next_idx < len(paragraphs):
        selected[-1] = selected[-1] + " ..."
    return selected


def fallback_excerpt(text: str, query: str, width: int = 850) -> str:
    pos = _match_position(text, query)
    start = max(0, pos - width // 3)
    end = min(len(text), start + width)
    out = re.sub(r"\s+", " ", text[start:end]).strip()
    if start > 0:
        out = "... " + out
    if end < len(text):
        out += " ..."
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Exam-focused context pack with keyword expansion and chunk-level retrieval.")
    parser.add_argument("question")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--source", default=None)
    parser.add_argument("--domain", choices=["history", "literature", "politics"], default=None)
    parser.add_argument("--include-worksheets", action="store_true")
    parser.add_argument("--include-low-value", action="store_true")
    args = parser.parse_args()

    auto_domain = infer_domain(args.question)
    active_domain = args.domain or auto_domain

    rows = run_query(
        args.question,
        limit=args.limit,
        source=args.source,
        exclude_worksheets=not args.include_worksheets,
        exclude_low_value=not args.include_low_value,
        domain=active_domain,
    )

    print("# Exam context pack\n")
    print(f"Question: {args.question}\n")
    print(f"Expanded query: `{build_query(args.question)}`")
    print(f"Domain: `{active_domain or 'none'}`\n")

    if not rows:
        print("No matches found. Try broader keywords, remove --source, or set a different --domain.")
        return

    for i, row in enumerate(rows, 1):
        print(f"## Hit {i}: {row['short_title']} p. {row['page_number']}")
        print(f"- Source ID: `{row['source_id']}`")
        print(f"- Kind: `{row['source_kind']}`")
        print(f"- Path: `{row['path']}`")
        if row["section_title"]:
            print(f"- Section: `{row['section_title']}` ({row['section_kind']})")
        if row["quality_flags"] != "[]":
            print(f"- Quality flags: `{row['quality_flags']}`")
        print()
        paragraphs = excerpt_paragraphs(row["text"], args.question)
        if not paragraphs:
            paragraphs = [fallback_excerpt(row["text"], args.question)]
        for paragraph in paragraphs:
            print(f"> {paragraph}\n")
        print()

    print("## Answer instruction\n")
    print("Give a thesis sentence, 3-7 factual points, then a short synthesis. Cite source path(s).")


if __name__ == "__main__":
    main()
