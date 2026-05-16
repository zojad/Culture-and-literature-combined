---
title: Quality notes
type: maintenance
status: active
last_updated: 2026-05-16
---

# Quality notes

The corpus is extracted from mixed materials (articles, handouts, outlines, lecture notes).

Known caveats:

- Some files are broad outlines and may be less precise than textbook passages.
- Some files are worksheet-like (`PD*`) and can be noisy for factual retrieval.
- OCR/source formatting issues may appear in punctuation or spacing.

When answer quality matters:

- prefer chunked retrieval (`python tools/exam_context.py ...`),
- prioritize article/textbook sections over worksheet chunks,
- cross-check dates/names across at least two relevant hits when possible.
