---
title: Schema and workflow
type: schema
status: active
last_updated: 2026-05-16
---

# Schema and workflow

This page summarizes LLM Wiki conventions for UK/US culture and literature exam support.

## Page types

- `index` — navigation and catalog pages.
- `log` — append-only chronological logs.
- `source` — source maps and source summaries.
- `concept` — history/literature concept pages.
- `question` — saved exam-answer pages.
- `glossary` — recurring terms.
- `maintenance` — lint reports and health checks.
- `plan` — future workflow plans.

## Required frontmatter

```yaml
---
title: Page title
type: concept
status: draft|active|needs_check|archived
last_updated: YYYY-MM-DD
sources:
  - brit_culture
  - brit_literature
  - us_culture
  - us_literature
---
```

## Citation discipline

Every durable factual claim should cite the corpus path.

Preferred citation shape:

> Source: Brit Culture, page 1, `data/corpus/pages/brit_culture/British Civilization An Introduction (John Oakland) 1 del.md`.

## Query workflow

1. Read [Wiki index](index.md) and [Exam wiki starter](exam/README.md).
2. Search wiki with `python tools/wiki_search.py "..."`.
3. Search corpus with `python tools/search.py "..."`.
4. Build context with `python tools/exam_context.py "..." --limit 8`.
5. Answer with thesis, key points, and citations.
6. Save recurring answers into `wiki/exam/questions/` and append `wiki/log.md`.

## Ingest workflow

1. Add source pages to `data/corpus/pages/<source_id>/`.
2. Rebuild index with `python tools/rebuild_index.py`.
3. Update source maps and exam pages.
4. Update `wiki/index.md` and `wiki/log.md`.
