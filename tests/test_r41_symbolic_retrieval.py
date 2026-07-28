"""MEC R4.1 — Symbolic and git-aware retrieval tests.

Tests symbol normalization, path matching, CLI detection, commit SHA matching,
entity grouping, and git history ingestion.
"""

from __future__ import annotations

import json
import unittest

from mec_lab.ingestion.symbol_normalize import (
    cli_options_match,
    commit_prefix_matches,
    extract_commit_prefix,
    normalize_cli_option,
    normalize_symbol,
    paths_symbol_match,
    symbols_match,
)
from mec_lab.ingestion.segmenters.python_ast import segment_python
from mec_lab.retrieval import AssistedRetriever, RetrievalState, StructuredScore
from mec_lab.storage import Storage
from tests.fixtures.portable_r41_project import PortableR41Project


class PortableR41TestCase(unittest.TestCase):
    """Provide each integration-test class with an isolated ingested project."""

    fixture: PortableR41Project
    store: Storage
    r: AssistedRetriever

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = PortableR41Project.create()
        cls.store = cls.fixture.storage
        cls.r = AssistedRetriever(cls.store)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture.close()


# ---------------------------------------------------------------------------
# Symbol normalization tests
# ---------------------------------------------------------------------------


class TestSymbolNormalization(unittest.TestCase):
    def test_pascalcase_splits(self) -> None:
        forms = normalize_symbol("ClarificationCycle")
        self.assertIn("clarification cycle", forms)
        self.assertIn("clarification_cycle", forms)
        self.assertIn("clarification-cycle", forms)

    def test_snake_case(self) -> None:
        forms = normalize_symbol("clarification_cycle")
        self.assertIn("clarification cycle", forms)
        self.assertIn("clarification_cycle", forms)

    def test_kebab_case(self) -> None:
        forms = normalize_symbol("clarification-cycle")
        self.assertIn("clarification cycle", forms)

    def test_dotted_module(self) -> None:
        forms = normalize_symbol("mec_lab.retrieval.assisted")
        self.assertIn("mec lab retrieval assisted", forms)
        self.assertIn("mec_lab_retrieval_assisted", forms)

    def test_path_with_slashes(self) -> None:
        forms = normalize_symbol("src/mec_lab/retrieval/assisted.py")
        self.assertIn("src/mec_lab/retrieval/assisted.py".lower(), forms)

    def test_symbols_match_pascalcase_words(self) -> None:
        self.assertTrue(symbols_match("ClarificationCycle", "clarification cycle"))
        self.assertTrue(symbols_match("ClarificationCycle", "clarification_cycle"))
        self.assertTrue(symbols_match("ClarificationCycle", "clarification-cycle"))

    def test_symbols_match_dotted_path(self) -> None:
        self.assertTrue(symbols_match("mec_lab.retrieval.assisted", "mec_lab/retrieval/assisted"))

    def test_symbols_dont_match_unrelated(self) -> None:
        self.assertFalse(symbols_match("ClarificationCycle", "Storage"))


# ---------------------------------------------------------------------------
# CLI option normalization
# ---------------------------------------------------------------------------


class TestCliNormalization(unittest.TestCase):
    def test_strip_dashes(self) -> None:
        self.assertEqual(normalize_cli_option("--retrieval-mode"), "retrieval_mode")
        self.assertEqual(normalize_cli_option("retrieval-mode"), "retrieval_mode")
        self.assertEqual(normalize_cli_option("--retrieval_mode"), "retrieval_mode")

    def test_cli_options_match(self) -> None:
        self.assertTrue(cli_options_match("--retrieval-mode", "retrieval_mode"))
        self.assertTrue(cli_options_match("retrieval-mode", "--retrieval_mode"))
        self.assertFalse(cli_options_match("--retrieval-mode", "source"))


# ---------------------------------------------------------------------------
# Path matching
# ---------------------------------------------------------------------------


class TestPathMatching(unittest.TestCase):
    def test_exact_path_unix(self) -> None:
        self.assertTrue(paths_symbol_match(
            "src/mec_lab/retrieval/assisted.py",
            "src/mec_lab/retrieval/assisted.py",
        ))

    def test_path_windows_unix(self) -> None:
        self.assertTrue(paths_symbol_match(
            "src\\mec_lab\\retrieval\\assisted.py",
            "src/mec_lab/retrieval/assisted.py",
        ))

    def test_path_basename(self) -> None:
        self.assertTrue(paths_symbol_match(
            "assisted.py",
            "src/mec_lab/retrieval/assisted.py",
        ))

    def test_path_unrelated(self) -> None:
        self.assertFalse(paths_symbol_match(
            "completely/different.py",
            "src/mec_lab/retrieval/assisted.py",
        ))


# ---------------------------------------------------------------------------
# Commit SHA matching
# ---------------------------------------------------------------------------


class TestCommitShaMatching(unittest.TestCase):
    SHA = "0d3833fc50aa7004c388de3495f97e099d844259"

    def test_extract_commit_prefix_with_keyword(self) -> None:
        self.assertEqual(
            extract_commit_prefix("commit 0d3833fc"),
            "0d3833fc",
        )
        self.assertEqual(
            extract_commit_prefix("SHA 0d3833fc"),
            "0d3833fc",
        )

    def test_extract_commit_prefix_standalone(self) -> None:
        self.assertEqual(
            extract_commit_prefix("0d3833fc50aa7004c388de3495f97e099d844259"),
            "0d3833fc50aa7004c388de3495f97e099d844259",
        )

    def test_prefix_matches_full(self) -> None:
        self.assertTrue(commit_prefix_matches("0d3833fc", self.SHA))
        self.assertTrue(commit_prefix_matches("0d3833fc50aa7004", self.SHA))
        self.assertTrue(commit_prefix_matches(self.SHA, self.SHA))

    def test_prefix_doesnt_match(self) -> None:
        self.assertFalse(commit_prefix_matches("ffffffff", self.SHA))
        self.assertFalse(commit_prefix_matches("abc1234", self.SHA))


# ---------------------------------------------------------------------------
# Python AST CLI detection
# ---------------------------------------------------------------------------


class TestCliAstDetection(unittest.TestCase):
    def test_click_command_detected(self) -> None:
        text = '''
import click

@click.command()
@click.option("--retrieval-mode", default="hybrid")
def search(query):
    """Search command."""
    pass
'''
        entities = segment_python(text, "cli.py")
        cmds = [e for e in entities if e.cli_command]
        opts = [e for e in entities if e.cli_option]
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].cli_command, "search")
        self.assertEqual(len(opts), 1)
        self.assertEqual(opts[0].cli_option, "--retrieval-mode")

    def test_cli_decorator_metadata(self) -> None:
        text = '''
@click.command("ingest-project")
def ingest_project():
    pass
'''
        entities = segment_python(text, "cli.py")
        cmds = [e for e in entities if e.cli_command]
        self.assertEqual(len(cmds), 1)
        self.assertEqual(cmds[0].cli_command, "ingest-project")


# ---------------------------------------------------------------------------
# Entity grouping tests
# ---------------------------------------------------------------------------


class TestEntityGrouping(PortableR41TestCase):
    """Multiple segments of the same file should not cause false ambiguity."""

    def test_exact_path_no_false_ambiguity(self) -> None:
        result = self.r.retrieve("src/mec_lab/retrieval/assisted.py")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)

    def test_class_exact_match(self) -> None:
        result = self.r.retrieve("ClarificationCycle")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)

    def test_assisted_retriever_class(self) -> None:
        result = self.r.retrieve("AssistedRetriever")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)

    def test_grouping_preserves_score_and_reports_segment_count(self) -> None:
        memories = [
            memory
            for memory in self.store.list_all_memories()
            if memory.metadata.get("source_path") == "src/mec_lab/retrieval/assisted.py"
        ]
        self.assertGreaterEqual(len(memories), 2)
        scores = [
            StructuredScore(memory_id=memories[0].id, final_score=0.8),
            StructuredScore(memory_id=memories[1].id, final_score=0.7),
        ]

        grouped = self.r._group_entities(scores)

        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0].final_score, 0.8)
        self.assertNotIn("entity_group_score", grouped[0].components())
        self.assertIn("2 segments grouped", grouped[0].match_reasons[-1])


# ---------------------------------------------------------------------------
# Commit retrieval tests
# ---------------------------------------------------------------------------


class TestCommitRetrieval(PortableR41TestCase):
    def test_commit_prefix_8_chars(self) -> None:
        result = self.r.retrieve(f"commit {self.fixture.head_sha[:8]}")
        self.assertIn(
            result.state,
            (RetrievalState.MEMORY_CONFIRMED, RetrievalState.AMBIGUOUS_CANDIDATES),
            f"Got {result.state.value}",
        )

    def test_sha_prefix_8_chars(self) -> None:
        result = self.r.retrieve(f"SHA {self.fixture.head_sha[:8]}")
        self.assertIn(
            result.state,
            (RetrievalState.MEMORY_CONFIRMED, RetrievalState.AMBIGUOUS_CANDIDATES),
        )

    def test_commit_full_sha(self) -> None:
        result = self.r.retrieve(f"commit {self.fixture.head_sha}")
        self.assertIn(
            result.state,
            (RetrievalState.MEMORY_CONFIRMED, RetrievalState.AMBIGUOUS_CANDIDATES),
        )

    def test_nonexistent_sha(self) -> None:
        result = self.r.retrieve("commit ffffffffffffffffffffffffffffffffffffffff")
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)
        if result.scores:
            for s in result.scores:
                self.assertEqual(s.commit_score, 0.0,
                    f"commit_score should be 0 for nonexistent SHA, got {s.commit_score}")


# ---------------------------------------------------------------------------
# Operational query tests
# ---------------------------------------------------------------------------


class TestOperationalQueries(PortableR41TestCase):
    """The 12 baseline queries — verify correctness post-R4.1."""

    def test_q1_clarification_cycle(self) -> None:
        r = self.r.retrieve("ClarificationCycle")
        self.assertEqual(r.state, RetrievalState.MEMORY_CONFIRMED)

    def test_q2_assisted_retriever(self) -> None:
        r = self.r.retrieve("AssistedRetriever")
        self.assertEqual(r.state, RetrievalState.MEMORY_CONFIRMED)

    def test_q3_exact_path(self) -> None:
        r = self.r.retrieve("src/mec_lab/retrieval/assisted.py")
        self.assertEqual(r.state, RetrievalState.MEMORY_CONFIRMED)

    def test_q4_dotted_module(self) -> None:
        r = self.r.retrieve("mec_lab.retrieval.assisted")
        self.assertEqual(r.state, RetrievalState.MEMORY_CONFIRMED)

    def test_q5_cli_search_command(self) -> None:
        r = self.r.retrieve("search --retrieval-mode assisted")
        # Command + option found — confirmed or ambiguous (both acceptable)
        self.assertIn(
            r.state,
            (RetrievalState.MEMORY_CONFIRMED, RetrievalState.AMBIGUOUS_CANDIDATES),
        )

    def test_q6_cli_ingest_command(self) -> None:
        r = self.r.retrieve("ingest-project")
        self.assertIn(
            r.state,
            (RetrievalState.MEMORY_CONFIRMED, RetrievalState.AMBIGUOUS_CANDIDATES),
        )

    def test_q7_commit_prefix(self) -> None:
        r = self.r.retrieve(f"commit {self.fixture.head_sha[:8]}")
        self.assertIn(
            r.state,
            (RetrievalState.MEMORY_CONFIRMED, RetrievalState.AMBIGUOUS_CANDIDATES),
        )

    def test_q8_sha_prefix(self) -> None:
        r = self.r.retrieve(f"SHA {self.fixture.head_sha[:8]}")
        self.assertIn(
            r.state,
            (RetrievalState.MEMORY_CONFIRMED, RetrievalState.AMBIGUOUS_CANDIDATES),
        )

    def test_q9_test_file_name(self) -> None:
        r = self.r.retrieve("test_r4_assisted_retrieval.py")
        self.assertEqual(r.state, RetrievalState.MEMORY_CONFIRMED)

    def test_q10_init_ambiguous(self) -> None:
        """init.py is genuinely ambiguous — multiple distinct __init__.py files."""
        r = self.r.retrieve("init.py")
        self.assertEqual(r.state, RetrievalState.AMBIGUOUS_CANDIDATES)
        source_paths = {
            memory.metadata.get("source_path", "")
            for memory in r.memories
            if memory.metadata.get("source_path")
        }
        self.assertGreaterEqual(len(source_paths), 2)

    def test_q11_storage_init(self) -> None:
        r = self.r.retrieve("storage init")
        self.assertIn(
            r.state,
            (RetrievalState.MEMORY_CONFIRMED, RetrievalState.AMBIGUOUS_CANDIDATES,
             RetrievalState.CLARIFICATION_REQUIRED),
        )

    def test_q12_absent(self) -> None:
        r = self.r.retrieve("blockchain smart contracts ethereum")
        self.assertEqual(r.state, RetrievalState.MEMORY_NOT_FOUND)


# ---------------------------------------------------------------------------
# R3 preservation
# ---------------------------------------------------------------------------


class TestR3Preserved(unittest.TestCase):
    def test_hybrid_retriever_still_works(self) -> None:
        from mec_lab.retrieval import HybridRetriever, DeterministicSemanticAdapter
        store = Storage(":memory:")
        store.init_schema()
        from mec_lab.domain.models import Fact
        store.save_memory(Fact(id="f1", content="SQLite armazenamento", project_id="p1"))
        retriever = HybridRetriever(store, semantic=DeterministicSemanticAdapter())
        result = retriever.search("SQLite")
        self.assertEqual(len(result.source_ids), 1)


if __name__ == "__main__":
    unittest.main()