"""Portable, deterministic R4.1 project fixture.

The fixture builds a real temporary Git repository, creates controlled commits,
runs the production ingestion pipeline with Git-history ingestion enabled, and
stores all memories in a temporary SQLite database.  Nothing depends on the
repository checkout path or on a pre-existing pilot database.
"""

from __future__ import annotations

import gc
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mec_lab.ingestion import IngestionPipeline
from mec_lab.storage import Storage


_BASE_FILES = {
    "README.md": """# Portable MEC fixture

This controlled project documents SQLite storage initialization and deterministic retrieval.
""",
    "pyproject.toml": """[project]
name = "portable-mec-fixture"
version = "1.0.0"
""",
    "src/mec_lab/__init__.py": '"""Portable MEC package."""\n',
    "src/mec_lab/retrieval/__init__.py": '"""Portable retrieval package."""\n',
    "src/mec_lab/storage/__init__.py": """\"\"\"Portable storage package.\"\"\"


def init_storage() -> str:
    return "SQLite storage initialized"
""",
}

_RETRIEVAL_FILES = {
    "src/mec_lab/retrieval/assisted.py": """\"\"\"Portable assisted retrieval implementation.\"\"\"


class ClarificationCycle:
    \"\"\"Deterministic clarification cycle for assisted memory retrieval.\"\"\"

    def start(self, query: str) -> str:
        return query


class AssistedRetriever:
    \"\"\"Retrieve structured memories and group sibling file segments.\"\"\"

    def retrieve(self, query: str) -> str:
        return query


def group_entities(source_path: str) -> str:
    \"\"\"Group segments from one source entity.\"\"\"
    return source_path
""",
    "src/mec_lab/cli/__init__.py": """\"\"\"Portable Click command surface.\"\"\"

import click


@click.group()
def cli() -> None:
    pass


@cli.command("search")
@click.option("--retrieval-mode", default="assisted")
def search(retrieval_mode: str) -> None:
    click.echo(retrieval_mode)


@cli.command("ingest-project")
def ingest_project() -> None:
    click.echo("ingested")
""",
    "src/mec_lab/ingestion/__init__.py": '"""Portable ingestion package."""\n',
    "tests/__init__.py": '"""Portable tests package."""\n',
    "tests/fixtures/__init__.py": '"""Portable test fixtures package."""\n',
    "tests/test_r4_assisted_retrieval.py": """def test_assisted_retrieval_contract() -> None:
    assert "assisted retrieval"
""",
}


def _write_files(root: Path, files: dict[str, str]) -> None:
    for relative_path, content in files.items():
        destination = root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8", newline="\n")


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _commit(root: Path, message: str, timestamp: str) -> str:
    _git(root, "add", "--all")
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "MEC Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "MEC Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
        "GIT_AUTHOR_DATE": timestamp,
        "GIT_COMMITTER_DATE": timestamp,
    })
    _git(root, "commit", "--quiet", "-m", message, env=env)
    return _git(root, "rev-parse", "HEAD")


@dataclass
class PortableR41Project:
    """Lifecycle holder for a fully ingested temporary R4.1 project."""

    _temporary_directory: tempfile.TemporaryDirectory[str]
    source_root: Path
    db_path: Path
    storage: Storage
    report: Any
    commit_shas: tuple[str, str]

    @property
    def head_sha(self) -> str:
        return self.commit_shas[-1]

    @classmethod
    def create(cls) -> "PortableR41Project":
        temporary_directory = tempfile.TemporaryDirectory(prefix="mec-r41-portable-")
        temporary_root = Path(temporary_directory.name)
        source_root = temporary_root / "project"
        source_root.mkdir()

        _git(source_root, "init", "--quiet")
        _git(source_root, "config", "core.autocrlf", "false")
        _write_files(source_root, _BASE_FILES)
        first_sha = _commit(
            source_root,
            "feat: initialize portable MEC project",
            "2026-01-01T00:00:00+00:00",
        )

        _write_files(source_root, _RETRIEVAL_FILES)
        second_sha = _commit(
            source_root,
            "feat: add portable assisted retrieval",
            "2026-01-02T00:00:00+00:00",
        )

        db_path = temporary_root / "portable-r41.db"
        storage = Storage(str(db_path))
        storage.init_schema()
        pipeline = IngestionPipeline(
            source_root=str(source_root),
            project_id="portable-r41-project",
            storage=storage,
            include_git_history=True,
        )
        report = pipeline.run()
        if report.errors:
            storage.conn.close()
            temporary_directory.cleanup()
            raise AssertionError(f"Portable fixture ingestion failed: {report.error_details}")

        return cls(
            _temporary_directory=temporary_directory,
            source_root=source_root,
            db_path=db_path,
            storage=storage,
            report=report,
            commit_shas=(first_sha, second_sha),
        )

    def close(self) -> None:
        self.storage.conn.close()
        # Click commands create their own short-lived Storage instance.  Force
        # collection before removing the temporary database so Windows releases
        # the SQLite file handle deterministically.
        gc.collect()
        self._temporary_directory.cleanup()

    def __enter__(self) -> "PortableR41Project":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
