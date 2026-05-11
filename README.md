# Slovenski jezik advisor

A private course repo for answering Slovenian language questions from a local corpus and for maintaining a persistent **LLM Wiki** over that corpus.

The repo currently contains two source layers:

1. **Slovenski pravopis 2001 - Pravila** (`sp2001`): orthography, capitalization, punctuation, writing together/apart, loanwords, hyphenation, abbreviations, symbols, and related normative questions.
2. **Jože Toporišič - Slovenska slovnica** (`toporisic_slovnica`): grammar, phonology, morphology, word formation, syntax, language varieties, communication, terminology, and historical language topics.

## LLM Wiki architecture in this repo

This repo now follows the LLM Wiki pattern:

- `data/raw/` — immutable raw source PDFs. They are included in this zip for local source-of-truth checking, but `.gitignore` prevents accidental Git commits unless you deliberately `git add -f` them for a private repository.
- `data/corpus/` — extracted page-level and combined Markdown derived from the PDFs. Treat this as source material, not as the persistent wiki.
- `wiki/` — the persistent, LLM-maintained Markdown wiki. This is where durable summaries, rule pages, contradictions, glossary entries, and filed answers should accumulate over time.
- `AGENTS.md` — the operating schema for Codex/Copilot/Claude-style agents.
- `wiki/index.md` — content-oriented index of wiki pages. Read this first when answering or maintaining the wiki.
- `wiki/log.md` — chronological append-only maintenance log.

## What is included

- `1200` page-level Markdown files in `data/corpus/pages/`.
- Combined source Markdown files in `data/corpus/combined/`.
- PDF outline exports in `data/corpus/outlines/`.
- Raw PDF copies in `data/raw/` for local checking.
- A prebuilt SQLite FTS5 index at `data/index/search.sqlite`.
- CLI helpers in `tools/` for corpus search, context packs, wiki search, wiki linting, and logging.
- Agent instructions in `AGENTS.md`, `.agents/skills/`, `.github/`, and `CLAUDE.md`.
- A starter persistent wiki in `wiki/`.

## Quick start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
python tools/search.py "vejica pred ki"
python tools/context.py "Ali se Novo mesto piše z veliko začetnico?"
python tools/wiki_search.py "naselbinska imena"
python tools/wiki_lint.py
```

## How one should ask

Ask in Slovenian or English, but require source-grounded answers:

> Kdaj pišemo vejico pred **ki**? Odgovori s citati na SP 2001 ali Toporišiča.

> Ali je pravilno **Novo mesto** ali **Novo Mesto**? Povej normativno pravilo in navedi stran.

## Source priority

For current normative spelling and punctuation, use **SP 2001** first. Use **Toporišič** to explain grammar, syntax, terminology, and the language system. If the two sources differ in emphasis, separate the normative answer from the explanatory grammar answer.

## Working with the wiki

The usual flow is:

1. Read `wiki/index.md`.
2. Search existing wiki pages with `python tools/wiki_search.py "..."`.
3. Search source extracts with `python tools/search.py "..."` and build context with `python tools/context.py "..."`.
4. Answer with citations to the source layer.
5. When the answer is durable, file or update a wiki page and append `wiki/log.md`.

## Copyright / privacy note

This repo contains extracted text from course-provided PDFs and local copies of the PDFs. Keep it private unless you have rights to redistribute the corpus. `.gitignore` intentionally excludes raw PDFs from normal `git add .`; for a private course repository, add them only if your permissions allow it:

```bash
git add -f data/raw/SP2001-4brez-zascite.pdf "data/raw/Jože Toporisic_Slovenska slovnica.pdf"
```
