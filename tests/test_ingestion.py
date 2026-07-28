"""MEC R4 — Ingestion pipeline tests.

Covers manifest generation, dry-run, segmentation, determinism, idempotency,
secret blocking, provenance metadata, CLI, and integration with R4 retrieval.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from mec_lab.cli import cli
from mec_lab.domain.enums import MemoryType
from mec_lab.ingestion import IngestionManifest, IngestionPipeline
from mec_lab.ingestion.identity import (
    content_fingerprint,
    stable_memory_id,
    stable_relation_id,
)
from mec_lab.ingestion.manifest import classify_file, sha256_file
from mec_lab.ingestion.secret_check import check_file, is_safe_file
from mec_lab.ingestion.segmenters.markdown import segment_markdown
from mec_lab.ingestion.segmenters.python_ast import segment_python
from mec_lab.ingestion.segmenters.config_files import segment_json, segment_toml, segment_yaml
from mec_lab.retrieval import AssistedRetriever, RetrievalState
from mec_lab.storage import Storage
from tests.fixtures.portable_r41_project import PortableR41Project


# ---------------------------------------------------------------------------
# Manifest tests
# ---------------------------------------------------------------------------


class TestManifest(unittest.TestCase):
    def test_classify_file_extensions(self) -> None:
        self.assertEqual(classify_file("readme.md"), "markdown")
        self.assertEqual(classify_file("src/module.py"), "python")
        self.assertEqual(classify_file("pyproject.toml"), "toml")
        self.assertEqual(classify_file("config.yaml"), "yaml")
        self.assertEqual(classify_file("config.yml"), "yaml")
        self.assertEqual(classify_file("data.json"), "json")
        self.assertEqual(classify_file("image.png"), "other")

    def test_sha256_file(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("hello world")
            f.flush()
            path = f.name
        h = sha256_file(path)
        self.assertEqual(len(h), 64)
        self.assertNotEqual(h, sha256_file(path + "x") if os.path.exists(path + "x") else "")
        os.unlink(path)

    def test_manifest_save_load_roundtrip(self) -> None:
        m = IngestionManifest(
            project_id="test-proj",
            source_root="/tmp/src",
            commit_sha="abc123",
            total_files=10,
            included_files=7,
            excluded_files=3,
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        m.save(path)
        m2 = IngestionManifest.load(path)
        self.assertEqual(m2.project_id, "test-proj")
        self.assertEqual(m2.total_files, 10)
        os.unlink(path)

    def test_failed_read_does_not_reuse_previous_file_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mec-manifest-read-") as temp_dir:
            root = Path(temp_dir)
            first = root / "first.py"
            second = root / "second.py"
            first.write_text(
                "class First:\n    pass\n\ndef first_function():\n    pass\n",
                encoding="utf-8",
            )
            second.write_text("class Second:\n    pass\n", encoding="utf-8")
            storage = Storage(":memory:")
            storage.init_schema()
            pipeline = IngestionPipeline(
                source_root=str(root),
                project_id="manifest-read-isolation",
                storage=storage,
            )
            pipeline._git_ls_files = lambda: ["first.py", "second.py"]  # type: ignore[method-assign]
            original_read_text = Path.read_text

            def controlled_read(path: Path, *args: object, **kwargs: object) -> str:
                if path == second:
                    raise OSError("controlled read failure")
                return original_read_text(path, *args, **kwargs)

            with patch.object(Path, "read_text", controlled_read):
                manifest = pipeline._build_manifest()

            entries = {entry.relative_path: entry for entry in manifest.files}
            self.assertEqual(entries["first.py"].status, "included")
            self.assertGreater(entries["first.py"].expected_segments, 0)
            self.assertEqual(entries["second.py"].status, "excluded")
            self.assertEqual(entries["second.py"].expected_segments, 0)
            self.assertEqual(entries["second.py"].exclusion_reason, "read error")
            self.assertEqual(pipeline.report.errors, 1)
            self.assertIn("read error: second.py", pipeline.report.error_details)
            storage.conn.close()


# ---------------------------------------------------------------------------
# Dry-run tests
# ---------------------------------------------------------------------------


class TestDryRun(unittest.TestCase):
    def test_dry_run_no_write(self) -> None:
        with PortableR41Project.create() as fixture:
            store = Storage(":memory:")
            store.init_schema()
            pipeline = IngestionPipeline(
                source_root=str(fixture.source_root),
                project_id="test-dry",
                storage=store,
                dry_run=True,
            )
            report = pipeline.run()
            self.assertGreater(report.files_analyzed, 0)
            self.assertEqual(report.memories_created, 0)
            self.assertEqual(report.relations_created, 0)
            store.conn.close()


# ---------------------------------------------------------------------------
# Segmenter tests
# ---------------------------------------------------------------------------


class TestMarkdownSegmenter(unittest.TestCase):
    def test_segment_by_headings(self) -> None:
        text = "# Title\n\nIntro text.\n\n## Section 1\n\nContent A.\n\n### Sub 1.1\n\nDetail.\n\n## Section 2\n\nContent B.\n"
        segs = segment_markdown(text, "doc.md", "My Doc")
        self.assertGreaterEqual(len(segs), 2)
        headings = [s.heading_chain[-1] for s in segs]
        self.assertIn("Section 1", headings)
        self.assertIn("Section 2", headings)

    def test_no_headings_single_segment(self) -> None:
        text = "Just a paragraph.\n\nAnother one."
        segs = segment_markdown(text, "doc.md", "My Doc")
        self.assertEqual(len(segs), 1)
        self.assertIn("Just a paragraph", segs[0].content)

    def test_empty_text(self) -> None:
        segs = segment_markdown("", "empty.md")
        self.assertEqual(len(segs), 0)

    def test_line_numbers_preserved(self) -> None:
        text = "# Title\n\nBody.\n\n## Section\n\nMore body.\n"
        segs = segment_markdown(text, "doc.md", "Doc")
        for s in segs:
            self.assertGreater(s.line_start, 0)
            self.assertGreaterEqual(s.line_end, s.line_start)

    def test_heading_chain_preserved(self) -> None:
        text = "# Top\n\n## Mid\n\n### Deep\n\nText.\n"
        segs = segment_markdown(text, "doc.md", "Doc")
        deep = [s for s in segs if "Deep" in s.heading_chain]
        self.assertEqual(len(deep), 1)
        self.assertEqual(deep[0].heading_chain, ["Top", "Mid", "Deep"])


class TestPythonSegmenter(unittest.TestCase):
    def test_class_and_method(self) -> None:
        text = '''
class MyClass:
    """A class."""
    def method(self, x: int) -> str:
        """Do something."""
        return str(x)
'''
        entities = segment_python(text, "test.py")
        types = {e.entity_type for e in entities}
        self.assertIn("module", types)
        self.assertIn("class", types)
        self.assertIn("method", types)

    def test_function_signature(self) -> None:
        text = '''
def greet(name: str, count: int = 1) -> str:
    """Say hello."""
    return f"Hello {name}" * count
'''
        entities = segment_python(text, "test.py")
        funcs = [e for e in entities if e.entity_type == "function"]
        self.assertEqual(len(funcs), 1)
        self.assertIn("name", funcs[0].signature)
        self.assertIn("count", funcs[0].signature)

    def test_docstring_extracted(self) -> None:
        text = '''
def has_doc():
    """This is a docstring."""
    pass
'''
        entities = segment_python(text, "test.py")
        funcs = [e for e in entities if e.entity_type == "function"]
        self.assertEqual(len(funcs), 1)
        self.assertIn("This is a docstring", funcs[0].docstring)

    def test_syntax_error_graceful(self) -> None:
        entities = segment_python("def broken(:", "broken.py")
        self.assertEqual(len(entities), 0)

    def test_qualified_names(self) -> None:
        text = '''
class Outer:
    class Inner:
        def method(self):
            pass
'''
        entities = segment_python(text, "pkg/mod.py")
        names = {e.qualified_name for e in entities}
        self.assertIn("Outer", names)
        self.assertIn("Outer.Inner", names)
        self.assertIn("Outer.Inner.method", names)


class TestConfigSegmenter(unittest.TestCase):
    def test_json_object(self) -> None:
        segs = segment_json('{"name": "test", "version": "1.0"}', "cfg.json")
        self.assertGreaterEqual(len(segs), 2)
        keys = {s.key_path for s in segs}
        self.assertIn("name", keys)
        self.assertIn("version", keys)

    def test_json_array(self) -> None:
        segs = segment_json('[{"a": 1}, {"b": 2}]', "list.json")
        self.assertGreaterEqual(len(segs), 2)
        self.assertEqual(segs[0].section_type, "list_item")

    def test_toml_table(self) -> None:
        segs = segment_toml('[project]\nname = "test"\nversion = "1.0"\n', "cfg.toml")
        keys = {s.key_path for s in segs}
        self.assertIn("project", keys)

    def test_yaml_sections(self) -> None:
        segs = segment_yaml("name: test\nversion: '1.0'\n", "cfg.yaml")
        keys = {s.key_path for s in segs}
        self.assertIn("name", keys)


# ---------------------------------------------------------------------------
# Identity tests
# ---------------------------------------------------------------------------


class TestIdentity(unittest.TestCase):
    def test_content_fingerprint_deterministic(self) -> None:
        a = content_fingerprint("hello")
        b = content_fingerprint("hello")
        self.assertEqual(a, b)

    def test_stable_memory_id_deterministic(self) -> None:
        a = stable_memory_id("proj", "path/to/file.py", "class", "MyClass")
        b = stable_memory_id("proj", "path/to/file.py", "class", "MyClass")
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)

    def test_different_params_different_ids(self) -> None:
        a = stable_memory_id("proj", "a.py", "class", "X")
        b = stable_memory_id("proj", "b.py", "class", "X")
        self.assertNotEqual(a, b)

    def test_stable_relation_id(self) -> None:
        a = stable_relation_id("mem1", "mem2", "part_of")
        b = stable_relation_id("mem1", "mem2", "part_of")
        self.assertEqual(a, b)


# ---------------------------------------------------------------------------
# Provenance metadata tests
# ---------------------------------------------------------------------------


class TestProvenanceMetadata(unittest.TestCase):
    def setUp(self) -> None:
        self.store = Storage(":memory:")
        self.store.init_schema()

    def test_memory_has_provenance(self) -> None:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test\n\nContent.\n")
            f.flush()
            path = f.name

        pipeline = IngestionPipeline(
            source_root=os.path.dirname(path),
            project_id="provenance-test",
            storage=self.store,
        )
        # Override git ls-files to include our file
        pipeline._git_ls_files = lambda: [os.path.basename(path)]  # type: ignore[method-assign]
        pipeline._get_git_commit = lambda: "test-commit-sha"  # type: ignore[method-assign]
        pipeline.run()

        memories = self.store.list_all_memories()
        self.assertGreater(len(memories), 0)
        for mem in memories:
            md = mem.metadata if hasattr(mem, "metadata") else {}
            self.assertIn("source_path", md)
            self.assertIn("source_sha256", md)
            self.assertIn("source_commit_sha", md)
            self.assertIn("ingestion_pipeline_version", md)
            self.assertIn("content_fingerprint", md)

        os.unlink(path)


# ---------------------------------------------------------------------------
# Idempotency tests
# ---------------------------------------------------------------------------


class TestIdempotency(unittest.TestCase):
    def test_double_ingestion_no_duplicates(self) -> None:
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def hello():\n    return 'world'\n")
            f.flush()
            path = f.name

        store = Storage(":memory:")
        store.init_schema()

        for run_label in ("first", "second"):
            pipeline = IngestionPipeline(
                source_root=os.path.dirname(path),
                project_id="idem-test",
                storage=store,
            )
            pipeline._git_ls_files = lambda: [os.path.basename(path)]  # type: ignore[method-assign]
            pipeline._get_git_commit = lambda: "sha1"  # type: ignore[method-assign]
            report = pipeline.run()

            if run_label == "first":
                self.assertGreater(report.memories_created, 0)
                first_count = report.memories_created
            else:
                self.assertEqual(report.memories_created, 0)
                self.assertEqual(report.memories_skipped, first_count)

        os.unlink(path)


# ---------------------------------------------------------------------------
# Secret blocking tests
# ---------------------------------------------------------------------------


class TestSecretBlocking(unittest.TestCase):
    def test_env_file_blocked(self) -> None:
        ok, reasons = is_safe_file("config/.env")
        self.assertFalse(ok)
        self.assertTrue(any("blocked filename" in r for r in reasons))

    def test_private_key_extension_blocked(self) -> None:
        ok, _ = is_safe_file("certs/server.key")
        self.assertFalse(ok)

    def test_api_key_content_blocked(self) -> None:
        ok, reasons = is_safe_file(
            "config.py",
            'API_KEY = "sk-1234567890abcdefghijklmnop"',
        )
        self.assertFalse(ok)

    def test_private_key_header_blocked(self) -> None:
        ok, _ = is_safe_file(
            "key.txt",
            "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkq...",
        )
        self.assertFalse(ok)

    def test_normal_file_not_blocked(self) -> None:
        ok, reasons = is_safe_file("readme.md", "# Hello\n\nThis is a readme.")
        self.assertTrue(ok)

    def test_no_secret_value_in_reason(self) -> None:
        """Reasons must never contain the actual secret."""
        result = check_file("config.py", 'API_KEY = "sk-my-secret-token-value-12345"')
        for reason in result.reasons:
            self.assertNotIn("sk-my-secret", reason)
            self.assertNotIn("token-value", reason)


# ---------------------------------------------------------------------------
# CLI ingestion tests
# ---------------------------------------------------------------------------


class TestCliIngestion(unittest.TestCase):
    fixture: PortableR41Project

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = PortableR41Project.create()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture.close()

    def setUp(self) -> None:
        self.runner = CliRunner()

    def test_ingest_help(self) -> None:
        result = self.runner.invoke(cli, ["ingest-project", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("--source", result.output)
        self.assertIn("--dry-run", result.output)

    def test_dry_run_json_output(self) -> None:
        result = self.runner.invoke(cli, [
            "ingest-project",
            "--source", str(self.fixture.source_root),
            "--db", ":memory:",
            "--project-id", "test-cli",
            "--dry-run",
            "--json",
        ])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output.strip())
        self.assertIn("files_analyzed", data)
        self.assertGreater(data["files_analyzed"], 0)
        self.assertEqual(data["memories_created"], 0)
        self.assertEqual(data["memories_skipped"], 0)

    def test_full_ingestion_json_output(self) -> None:
        result = self.runner.invoke(cli, [
            "ingest-project",
            "--source", str(self.fixture.source_root),
            "--db", ":memory:",
            "--project-id", "test-cli-full",
            "--json",
            "--force-reindex",
        ])
        self.assertEqual(result.exit_code, 0)
        data = json.loads(result.output.strip())
        self.assertIn("memories_created", data)
        # Dry-run should produce 0, live should produce >0
        self.assertGreater(data["memories_created"], 0, f"Got {data['memories_created']}")


# ---------------------------------------------------------------------------
# R4 retrieval over ingested DB tests
# ---------------------------------------------------------------------------


class TestR4OverIngestedDb(unittest.TestCase):
    """Verify that R4 can search a freshly ingested portable database."""

    fixture: PortableR41Project

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = PortableR41Project.create()
        cls.store = cls.fixture.storage
        cls.retriever = AssistedRetriever(cls.store)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture.close()

    def test_pilot_db_has_memories(self) -> None:
        count = self.store.count_memories()
        self.assertGreater(count, 10, f"Expected >10 portable memories, got {count}")

    def test_pilot_db_has_relations(self) -> None:
        rels = self.store.list_all_relations()
        self.assertGreater(len(rels), 5)

    def test_r4_path_query_returns_results(self) -> None:
        result = self.retriever.retrieve("src/mec_lab/retrieval/assisted.py")
        self.assertNotEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)

    def test_r4_confirmed_state_exists(self) -> None:
        result = self.retriever.retrieve("src/mec_lab/retrieval/assisted.py")
        self.assertIn(
            result.state,
            (RetrievalState.MEMORY_CONFIRMED, RetrievalState.AMBIGUOUS_CANDIDATES),
            f"Got {result.state.value}",
        )

    def test_r4_not_found_state_exists(self) -> None:
        result = self.retriever.retrieve("zzz_nonexistent_xyz_12345_abc")
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)


# ---------------------------------------------------------------------------
# R3 regression tests
# ---------------------------------------------------------------------------


class TestR3NotBroken(unittest.TestCase):
    def test_hybrid_retriever_still_works(self) -> None:
        from mec_lab.retrieval import HybridRetriever, DeterministicSemanticAdapter
        store = Storage(":memory:")
        store.init_schema()
        from mec_lab.domain.models import Fact
        store.save_memory(Fact(id="f1", content="SQLite armazenamento", project_id="p1"))
        retriever = HybridRetriever(store, semantic=DeterministicSemanticAdapter())
        result = retriever.search("SQLite")
        self.assertEqual(len(result.source_ids), 1)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()
