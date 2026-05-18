#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "index" / "search.sqlite"


def build_query(q: str, operator: str = "and") -> str:
    tokens = re.findall(r"[\wčšžćđČŠŽĆĐ]+", q, flags=re.UNICODE)
    tokens = [t for t in tokens if len(t) > 1]
    if not tokens:
        return '""'
    sep = " AND " if operator == "and" else " OR "
    return sep.join(tokens)


def table_exists(cur: sqlite3.Cursor, table_name: str) -> bool:
    row = cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table_name,)).fetchone()
    return row is not None


def get_rows(query: str, limit: int):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if table_exists(cur, "chunks_fts"):
        sql = """
            SELECT c.id, c.source_id, c.short_title, c.source_kind, c.page_number, c.path,
                   c.section_title, c.quality_flags, c.text,
                   bm25(chunks_fts) AS rank
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """
    else:
        sql = """
            SELECT p.id, p.source_id, p.short_title, p.source_kind, p.page_number, p.path,
                   '' as section_title, p.quality_flags, p.text,
                   bm25(pages_fts) AS rank
            FROM pages_fts
            JOIN pages p ON p.id = pages_fts.rowid
            WHERE pages_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """

    rows = cur.execute(sql, [build_query(query, "and"), limit]).fetchall()
    if not rows:
        rows = cur.execute(sql, [build_query(query, "or"), limit]).fetchall()
    conn.close()
    return rows


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
    tokens = [t.lower() for t in re.findall(r"[\wčšžćđČŠŽĆĐ]+", query, flags=re.UNICODE) if len(t) > 1]
    lower = text.lower()
    for tok in tokens:
        pos = lower.find(tok)
        if pos >= 0:
            return pos
    return 0


def excerpt_paragraphs(text: str, query: str, width: int = 900) -> list[str]:
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


def fallback_excerpt(text: str, query: str, width: int = 900) -> str:
    pos = _match_position(text, query)
    start = max(0, pos - width // 3)
    end = min(len(text), start + width)
    out = text[start:end]
    out = re.sub(r"\s+", " ", out).strip()
    if start > 0:
        out = "... " + out
    if end < len(text):
        out += " ..."
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an LLM context pack from local corpus search results.")
    parser.add_argument("question")
    parser.add_argument("--limit", type=int, default=6)
    args = parser.parse_args()
    rows = get_rows(args.question, args.limit)
    print(f"# Context pack\n\nQuestion: {args.question}\n")
    if not rows:
        print("No local matches found. Try fewer words or a synonym.")
        return
    for i, row in enumerate(rows, 1):
        print(f"## Source {i}: {row['short_title']}, PDF page {row['page_number']}\n")
        print(f"- Source ID: `{row['source_id']}`")
        print(f"- Kind: `{row['source_kind']}`")
        print(f"- Markdown path: `{row['path']}`")
        if row["section_title"]:
            print(f"- Section: `{row['section_title']}`")
        if row['quality_flags'] != "[]":
            print(f"- Quality flags: `{row['quality_flags']}`")
        print()
        paragraphs = excerpt_paragraphs(row["text"], args.question)
        if not paragraphs:
            paragraphs = [fallback_excerpt(row["text"], args.question)]
        for paragraph in paragraphs:
            print(f"> {paragraph}\n")
        print()
    print("## Instruction for answer\n")
    print("Answer from these sources only. Give a thesis first, then key points, and cite Markdown paths.")


if __name__ == "__main__":
    main()
