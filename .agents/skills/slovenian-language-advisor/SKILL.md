---
name: culture-literature-exam-advisor
description: Answer UK/US culture and literature exam questions from local corpus sources while maintaining the persistent exam wiki.
---

# Culture and literature exam advisor skill

Use this skill when tasks involve:

- British history/culture topics,
- American culture topics,
- UK/US literature periods, authors, and works,
- exam-style prompts matching `questions_ff`.

## Workflow

1. Read `AGENTS.md` and `wiki/exam/README.md`.
2. Search wiki with `python tools/wiki_search.py "<query>"`.
3. Build retrieval context with `python tools/exam_context.py "<query>" --limit 8`.
4. Read the most relevant hits.
5. Answer in exam format (thesis, key points, synthesis, citations).
6. Save durable answers under `wiki/exam/questions/` and append `wiki/log.md`.
