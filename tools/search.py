#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "index" / "search.sqlite"
PAGES_DIR = ROOT / "data" / "corpus" / "pages"


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


def search(query: str, limit: int = 10, source: str | None = None) -> list[sqlite3.Row]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    fts_query = build_query(query, "and")

    if table_exists(cur, "chunks_fts"):
        where_source = " AND c.source_id = ?" if source else ""
        params: list[object] = [fts_query]
        if source:
            params.append(source)
        params.append(limit)
        sql = f"""
            SELECT c.id, c.source_id, c.short_title, c.source_kind, c.page_number, c.path,
                   c.section_title,
                   snippet(chunks_fts, 0, '[', ']', ' ... ', 18) AS snippet,
                   bm25(chunks_fts) AS rank
            FROM chunks_fts
            JOIN chunks c ON c.id = chunks_fts.rowid
            WHERE chunks_fts MATCH ?{where_source}
            ORDER BY rank
            LIMIT ?
        """
    else:
        where_source = " AND source_id = ?" if source else ""
        params = [fts_query]
        if source:
            params.append(source)
        params.append(limit)
        sql = f"""
            SELECT rowid as id, source_id, short_title, source_kind, page_number, path,
                   '' as section_title,
                   snippet(pages_fts, 0, '[', ']', ' ... ', 18) AS snippet,
                   bm25(pages_fts) AS rank
            FROM pages_fts
            WHERE pages_fts MATCH ?{where_source}
            ORDER BY rank
            LIMIT ?
        """

    rows = cur.execute(sql, params).fetchall()
    if not rows and len(re.findall(r"[\wčšžćđČŠŽĆĐ]+", query, flags=re.UNICODE)) > 1:
        fts_query = build_query(query, "or")
        params = [fts_query]
        if source:
            params.append(source)
        params.append(limit)
        rows = cur.execute(sql, params).fetchall()
    conn.close()
    return rows


def main() -> None:
    source_choices = sorted(p.name for p in PAGES_DIR.iterdir() if p.is_dir()) if PAGES_DIR.exists() else []
    parser = argparse.ArgumentParser(description="Search the local corpus.")
    parser.add_argument("query")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--source", choices=source_choices if source_choices else None, default=None)
    args = parser.parse_args()
    for i, row in enumerate(search(args.query, args.limit, args.source), 1):
        section = f" | section: {row['section_title']}" if row["section_title"] else ""
        print(f"{i}. {row['short_title']} p. {row['page_number']} [{row['source_id']}] {row['path']}{section}")
        print(f"   {row['snippet']}")


if __name__ == "__main__":
    main()
