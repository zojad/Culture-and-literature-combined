# Copilot custom instructions

This repository answers UK/US culture and literature exam questions from a local corpus and maintains a persistent wiki.

When generating answers or code:

- Read `AGENTS.md` for workflow.
- Search `wiki/index.md` and `wiki/exam/` before broad answers.
- Use `python tools/search.py "..."`, `python tools/context.py "..."`, and `python tools/exam_context.py "..."`.
- Cite corpus Markdown paths for factual claims.
- Prefer exam-style output: thesis, key points, short synthesis, citations.
- For recurring answers, update `wiki/exam/questions/` and append `wiki/log.md`.
