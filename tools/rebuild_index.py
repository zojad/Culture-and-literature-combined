#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES_ROOT = ROOT / "data" / "corpus" / "pages"
DB_PATH = ROOT / "data" / "index" / "search.sqlite"
MANIFEST_PATH = ROOT / "data" / "manifest.jsonl"


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
WORD_RE = re.compile(r"[\wČŠŽčšžĆćĐđ]+", flags=re.UNICODE)


def source_kind_for(source_id: str) -> str:
    if "culture" in source_id:
        return "culture"
    if "literature" in source_id:
        return "literature"
    return "general"


def split_into_sections(text: str, fallback_title: str) -> list[tuple[str, str]]:
    lines = text.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title = fallback_title
    current_lines: list[str] = []

    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            if current_lines:
                sections.append((current_title, current_lines))
                current_lines = []
            current_title = m.group(2).strip()
        current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    out: list[tuple[str, str]] = []
    for title, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if body:
            out.append((title, body))

    if not out:
        out.append((fallback_title, text.strip()))
    return out


def classify_path(path_name: str) -> str:
    low = path_name.lower()
    if "handout" in low:
        return "handout"
    if low.startswith("pd"):
        return "worksheet"
    if "outline" in low:
        return "outline"
    if "lecture" in low:
        return "lecture"
    return "article"


def build_index() -> tuple[int, int, int]:
    sources = sorted([p for p in PAGES_ROOT.iterdir() if p.is_dir()])

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE pages (
            id INTEGER PRIMARY KEY,
            source_id TEXT NOT NULL,
            source_title TEXT NOT NULL,
            short_title TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            path TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            word_count INTEGER NOT NULL,
            quality_flags TEXT NOT NULL,
            text TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE VIRTUAL TABLE pages_fts USING fts5(
            text,
            source_id UNINDEXED,
            source_title UNINDEXED,
            short_title UNINDEXED,
            source_kind UNINDEXED,
            page_number UNINDEXED,
            path UNINDEXED,
            content='pages',
            content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE chunks (
            id INTEGER PRIMARY KEY,
            source_id TEXT NOT NULL,
            source_title TEXT NOT NULL,
            short_title TEXT NOT NULL,
            source_kind TEXT NOT NULL,
            page_number INTEGER NOT NULL,
            path TEXT NOT NULL,
            section_title TEXT NOT NULL,
            section_order INTEGER NOT NULL,
            section_kind TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            word_count INTEGER NOT NULL,
            quality_flags TEXT NOT NULL,
            text TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE VIRTUAL TABLE chunks_fts USING fts5(
            text,
            section_title,
            source_id UNINDEXED,
            source_title UNINDEXED,
            short_title UNINDEXED,
            source_kind UNINDEXED,
            page_number UNINDEXED,
            path UNINDEXED,
            section_kind UNINDEXED,
            content='chunks',
            content_rowid='id',
            tokenize='unicode61 remove_diacritics 2'
        )
        """
    )

    page_id = 1
    chunk_id = 1
    manifest_lines: list[str] = []

    for source_dir in sources:
        source_id = source_dir.name
        source_title = source_id.replace("_", " ").title()
        short_title = source_title
        source_kind = source_kind_for(source_id)

        md_files = sorted(source_dir.glob("*.md"), key=lambda p: p.name.lower())
        page_count = len(md_files)

        for page_number, md in enumerate(md_files, start=1):
            text = md.read_text(encoding="utf-8", errors="replace").replace("\x00", " ")
            words = WORD_RE.findall(text)
            word_count = len(words)
            char_count = len(text)
            rel_path = md.as_posix()

            quality_flags: list[str] = []
            if word_count == 0:
                quality_flags.append("empty_text_layer")
            if word_count < 20:
                quality_flags.append("low_text_needs_visual_check")

            cur.execute(
                """
                INSERT INTO pages(id, source_id, source_title, short_title, source_kind, page_number, path, char_count, word_count, quality_flags, text)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    page_id,
                    source_id,
                    source_title,
                    short_title,
                    source_kind,
                    page_number,
                    rel_path,
                    char_count,
                    word_count,
                    json.dumps(quality_flags, ensure_ascii=False),
                    text,
                ),
            )
            cur.execute(
                """
                INSERT INTO pages_fts(rowid, text, source_id, source_title, short_title, source_kind, page_number, path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (page_id, text, source_id, source_title, short_title, source_kind, page_number, rel_path),
            )

            section_kind = classify_path(md.name)
            sections = split_into_sections(text, md.stem)
            for section_order, (section_title, section_text) in enumerate(sections, start=1):
                sec_words = WORD_RE.findall(section_text)
                sec_flags = []
                if len(sec_words) < 15:
                    sec_flags.append("short_section")
                cur.execute(
                    """
                    INSERT INTO chunks(id, source_id, source_title, short_title, source_kind, page_number, path, section_title, section_order, section_kind, char_count, word_count, quality_flags, text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        source_id,
                        source_title,
                        short_title,
                        source_kind,
                        page_number,
                        rel_path,
                        section_title,
                        section_order,
                        section_kind,
                        len(section_text),
                        len(sec_words),
                        json.dumps(sec_flags, ensure_ascii=False),
                        section_text,
                    ),
                )
                cur.execute(
                    """
                    INSERT INTO chunks_fts(rowid, text, section_title, source_id, source_title, short_title, source_kind, page_number, path, section_kind)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk_id,
                        section_text,
                        section_title,
                        source_id,
                        source_title,
                        short_title,
                        source_kind,
                        page_number,
                        rel_path,
                        section_kind,
                    ),
                )
                chunk_id += 1

            manifest_lines.append(
                json.dumps(
                    {
                        "source_id": source_id,
                        "source_title": source_title,
                        "short_title": short_title,
                        "source_kind": source_kind,
                        "pdf_filename": None,
                        "page_number": page_number,
                        "page_count": page_count,
                        "path": rel_path,
                        "char_count": char_count,
                        "word_count": word_count,
                        "quality_flags": quality_flags,
                    },
                    ensure_ascii=False,
                )
            )

            page_id += 1

    conn.commit()
    conn.close()

    MANIFEST_PATH.write_text("\n".join(manifest_lines) + ("\n" if manifest_lines else ""), encoding="utf-8")

    return len(sources), page_id - 1, chunk_id - 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild SQLite index from markdown corpus with heading-based chunks.")
    args = parser.parse_args()
    source_count, pages, chunks = build_index()
    print(f"Rebuilt {DB_PATH} from {source_count} sources: {pages} pages, {chunks} chunks.")
    print(f"Updated {MANIFEST_PATH}.")


if __name__ == "__main__":
    main()
