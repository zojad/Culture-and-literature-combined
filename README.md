# Culture and Literature Exam Wiki

A private course repo for answering British/American culture and literature exam questions from a local corpus and maintaining a persistent LLM Wiki.

## Current corpus sources

- `brit_culture`
- `brit_literature`
- `us_culture`
- `us_literature`

## Quick start

```bash
python tools/search.py "british empire commonwealth"
python tools/context.py "Magna Carta and Domesday Book significance" --limit 6
python tools/exam_context.py "Comment on British Empire and Commonwealth" --limit 8
python tools/wiki_search.py "anglo-saxon norman victorian"
python tools/wiki_lint.py
```

## Wiki structure

- `wiki/exam/` — exam-focused pages (themes, history, literature, timelines, question bank).
- `wiki/index.md` — top-level navigation.
- `wiki/log.md` — maintenance history.

## Notes

- Source files in `data/corpus/pages/` are treated as immutable reference material.
- Rebuild index after source changes with `python tools/rebuild_index.py`.
