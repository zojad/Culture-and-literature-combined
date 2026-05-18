from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]


def test_index_exists_and_has_exam_sources():
    db = ROOT / "data" / "index" / "search.sqlite"
    assert db.exists()
    conn = sqlite3.connect(db)
    rows = conn.execute("SELECT source_id, COUNT(*) FROM pages GROUP BY source_id").fetchall()
    conn.close()
    counts = dict(rows)
    assert counts.get("brit_culture", 0) >= 3
    assert counts.get("brit_literature", 0) >= 2
    assert counts.get("us_culture", 0) >= 50
    assert counts.get("us_literature", 0) >= 2


def test_markdown_pages_exist():
    assert (
        ROOT
        / "data"
        / "corpus"
        / "pages"
        / "brit_culture"
        / "British Civilization An Introduction (John Oakland) 1 del.md"
    ).exists()
    assert (ROOT / "data" / "corpus" / "pages" / "brit_literature" / "British Literature Lectures.md").exists()
    assert (ROOT / "data" / "corpus" / "pages" / "us_culture" / "constitution.md").exists()
    assert (ROOT / "data" / "corpus" / "pages" / "us_literature" / "Amlitberilo.md").exists()


def test_search_finds_exam_terms():
    conn = sqlite3.connect(ROOT / "data" / "index" / "search.sqlite")
    n = conn.execute("SELECT COUNT(*) FROM pages_fts WHERE pages_fts MATCH 'Commonwealth OR \"Magna Carta\"'").fetchone()[0]
    conn.close()
    assert n > 0


def test_llm_wiki_core_files_exist():
    assert (ROOT / "wiki" / "index.md").exists()
    assert (ROOT / "wiki" / "log.md").exists()
    assert (ROOT / "wiki" / "exam" / "README.md").exists()
    assert (ROOT / "wiki" / "exam" / "questions" / "exam-question-bank.md").exists()
    assert (ROOT / "wiki" / "exam" / "themes" / "british-empire-and-commonwealth.md").exists()
    assert (ROOT / "AGENTS.md").read_text(encoding="utf-8").count("Exam Wiki") >= 1


def test_raw_source_readme_present_in_bundle():
    assert (ROOT / "data" / "raw" / "README.md").exists()


def test_wiki_lint_script_runs():
    import subprocess
    result = subprocess.run(["python", str(ROOT / "tools" / "wiki_lint.py")], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
