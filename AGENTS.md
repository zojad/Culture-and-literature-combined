# AGENTS.md - UK/US Culture and Literature Exam Wiki

This repo is a private course corpus and persistent LLM Wiki for answering exam-style questions in British and American culture/literature.

## Core principle

Do not behave like a generic chatbot over uploaded documents. Maintain a compounding wiki that improves with each question.

- Raw sources are immutable: `data/raw/` and `data/corpus/` are source layers.
- The persistent wiki is `wiki/`.
- Exam-focused additive structure is under `wiki/exam/`.

## Non-negotiables

- Answer only from the local corpus unless the user explicitly asks for external sources.
- Cite every substantive claim with source title and Markdown path.
- Prefer concise, oral-exam-ready answers first, then detail.
- If a fact is uncertain in corpus, state uncertainty and show best available evidence.
- Do not invent dates, author names, titles, or historical events.
- Read `wiki/exam/README.md` and `wiki/exam/questions/exam-question-bank.md` before broad exam answers.

## Source routing

Primary source IDs in this repo:

- `brit_culture`
- `brit_literature`
- `us_culture`
- `us_literature`

Use culture sources first for history/politics/institutions; literature sources first for authors/periods/works. Use both when a question mixes historical context and literary development.

## Exam question patterns

Reference question patterns are stored in:

- `questions_ff/Izpit Družbe in kulture - enopredmetni - ustni del.md`
- `questions_ff/Izpit Dr in kulture - dvopredmetni - ustni del.md`
- normalized wiki mapping: `wiki/exam/questions/questions-ff-reference.md`

Typical prompts include:

- British Empire / Commonwealth
- key British historical periods
- authors + works by period
- monarch significance (Anglo-Saxon/Norman)
- Magna Carta / Domesday Book
- quick factual prompts (when/what/who)

## Query workflow

1. Read `wiki/exam/README.md`.
2. Search wiki pages: `python tools/wiki_search.py "<question or key terms>"`.
3. Search corpus and build context:
   - `python tools/search.py "<question>"`
   - `python tools/context.py "<question>" --limit 8`
4. Read the most relevant source pages, not only snippets.
5. Answer in exam style and cite file paths.
6. If recurring, file/improve the answer under `wiki/exam/questions/` and append `wiki/log.md`.
