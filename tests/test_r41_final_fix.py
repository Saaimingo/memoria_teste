"""MEC R4.1 final fix — full idempotency and identifier absence.

Permanent regression coverage for:
* two-phase Git relation creation;
* canonical database-state stability across three ingestions;
* negative constraints for explicit identifiers;
* preservation of text, symbolic, ambiguous, absent, and R3 retrieval.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from mec_lab.cli import cli
from mec_lab.domain.models import Decision, Fact, Hypothesis
from mec_lab.ingestion import IngestionPipeline
from mec_lab.retrieval import (
    AssistedRetriever,
    AssistedRetrievalConfig,
    DeterministicSemanticAdapter,
    HybridRetriever,
    IdentifierConstraintStatus,
    RetrievalState,
)
from mec_lab.storage import Storage
from tests.fixtures.operational_fixture import (
    COMMIT_FULL_A,
    build_fixture_storage,
)
from tests.fixtures.portable_r41_project import PortableR41Project


GIT_COMMITS = [
    {
        "sha": "3333333333333333333333333333333333333333",
        "parents": ["2222222222222222222222222222222222222222"],
        "author": "Test Author",
        "date": "2026-01-03T00:00:00+00:00",
        "message": "third commit",
        "files": ["third.py"],
        "insertions": 3,
        "deletions": 0,
    },
    {
        "sha": "2222222222222222222222222222222222222222",
        "parents": ["1111111111111111111111111111111111111111"],
        "author": "Test Author",
        "date": "2026-01-02T00:00:00+00:00",
        "message": "second commit",
        "files": ["second.py"],
        "insertions": 2,
        "deletions": 0,
    },
    {
        "sha": "1111111111111111111111111111111111111111",
        "parents": [],
        "author": "Test Author",
        "date": "2026-01-01T00:00:00+00:00",
        "message": "first commit",
        "files": ["first.py"],
        "insertions": 1,
        "deletions": 0,
    },
]


def canonical_database_summary(storage: Storage) -> dict:
    """Return a SQLite-internal-independent canonical state summary."""
    memories = sorted(storage.list_all_memories(), key=lambda m: m.id)
    relations = sorted(storage.list_all_relations(), key=lambda r: r.id)
    memory_types = Counter(
        m.type.value if hasattr(m.type, "value") else str(m.type)
        for m in memories
    )
    relation_types = Counter(
        r.relation_type.value if hasattr(r.relation_type, "value") else str(r.relation_type)
        for r in relations
    )
    return {
        "memories": [
            {
                "id": m.id,
                "fingerprint": m.metadata.get("content_fingerprint", ""),
                "type": m.type.value if hasattr(m.type, "value") else str(m.type),
            }
            for m in memories
        ],
        "relations": [
            {
                "id": r.id,
                "source_id": r.source_id,
                "target_id": r.target_id,
                "type": (
                    r.relation_type.value
                    if hasattr(r.relation_type, "value")
                    else str(r.relation_type)
                ),
            }
            for r in relations
        ],
        "totals": {
            "memories": len(memories),
            "relations": len(relations),
            "memory_types": dict(sorted(memory_types.items())),
            "relation_types": dict(sorted(relation_types.items())),
        },
    }


def canonical_hash(storage: Storage) -> str:
    payload = json.dumps(
        canonical_database_summary(storage),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def run_git_ingestion(db_path: str, commits: list[dict]) -> tuple[object, str]:
    storage = Storage(db_path)
    storage.init_schema()
    pipeline = IngestionPipeline(
        source_root=str(Path(db_path).parent),
        project_id="r41-final-fix-test",
        storage=storage,
        include_git_history=True,
    )
    with patch.object(pipeline, "_get_git_log", return_value=commits):
        pipeline._ingest_git_history()
    state_hash = canonical_hash(storage)
    report = pipeline.report
    storage.conn.close()
    return report, state_hash


class TestFullIngestionIdempotency(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp.close()
        self.db_path = tmp.name

    def tearDown(self) -> None:
        Path(self.db_path).unlink(missing_ok=True)

    def test_01_first_ingestion_creates_all_memories(self) -> None:
        report, _ = run_git_ingestion(self.db_path, GIT_COMMITS)
        self.assertEqual(report.memories_created, 3)

    def test_02_first_ingestion_creates_all_relations(self) -> None:
        report, _ = run_git_ingestion(self.db_path, GIT_COMMITS)
        self.assertEqual(report.relations_created, 2)

    def test_03_second_ingestion_creates_zero_memories(self) -> None:
        run_git_ingestion(self.db_path, GIT_COMMITS)
        report, _ = run_git_ingestion(self.db_path, GIT_COMMITS)
        self.assertEqual(report.memories_created, 0)

    def test_04_second_ingestion_creates_zero_relations(self) -> None:
        run_git_ingestion(self.db_path, GIT_COMMITS)
        report, _ = run_git_ingestion(self.db_path, GIT_COMMITS)
        self.assertEqual(report.relations_created, 0)

    def test_05_third_ingestion_creates_zero_memories(self) -> None:
        run_git_ingestion(self.db_path, GIT_COMMITS)
        run_git_ingestion(self.db_path, GIT_COMMITS)
        report, _ = run_git_ingestion(self.db_path, GIT_COMMITS)
        self.assertEqual(report.memories_created, 0)

    def test_06_third_ingestion_creates_zero_relations(self) -> None:
        run_git_ingestion(self.db_path, GIT_COMMITS)
        run_git_ingestion(self.db_path, GIT_COMMITS)
        report, _ = run_git_ingestion(self.db_path, GIT_COMMITS)
        self.assertEqual(report.relations_created, 0)

    def test_07_canonical_hash_equal_after_three_runs(self) -> None:
        _, h1 = run_git_ingestion(self.db_path, GIT_COMMITS)
        _, h2 = run_git_ingestion(self.db_path, GIT_COMMITS)
        _, h3 = run_git_ingestion(self.db_path, GIT_COMMITS)
        self.assertEqual(h1, h2)
        self.assertEqual(h2, h3)

    def test_08_commit_parent_relations_exist_on_first_run(self) -> None:
        run_git_ingestion(self.db_path, GIT_COMMITS)
        storage = Storage(self.db_path)
        storage.init_schema()
        relations = storage.list_all_relations()
        self.assertEqual(len(relations), 2)
        self.assertTrue(all(str(r.relation_type) == "derived_from" for r in relations))
        storage.conn.close()

    def test_09_commit_enumeration_order_does_not_change_state(self) -> None:
        _, forward_hash = run_git_ingestion(self.db_path, GIT_COMMITS)
        Path(self.db_path).unlink(missing_ok=True)
        _, reverse_hash = run_git_ingestion(self.db_path, list(reversed(GIT_COMMITS)))
        self.assertEqual(forward_hash, reverse_hash)

    def test_10_sqlite_reopen_preserves_idempotency(self) -> None:
        run_git_ingestion(self.db_path, GIT_COMMITS)
        before = Storage(self.db_path)
        before.init_schema()
        before_hash = canonical_hash(before)
        before.conn.close()
        report, after_hash = run_git_ingestion(self.db_path, GIT_COMMITS)
        self.assertEqual(report.memories_created, 0)
        self.assertEqual(report.relations_created, 0)
        self.assertEqual(before_hash, after_hash)


class IdentifierConstraintFixtureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.storage = build_fixture_storage()
        self.retriever = AssistedRetriever(self.storage)

    def tearDown(self) -> None:
        self.storage.conn.close()

    def test_11_existing_full_commit_sha(self) -> None:
        result = self.retriever.retrieve(f"commit {COMMIT_FULL_A}")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)
        self.assertEqual(result.top_memory().id, "mec-ev1")

    def test_12_existing_unique_commit_prefix(self) -> None:
        result = self.retriever.retrieve("commit a1b2c3d")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)
        self.assertEqual(result.identifier_constraint_status, "IDENTIFIER_MATCHED_UNIQUE")

    def test_13_ambiguous_commit_prefix(self) -> None:
        storage = Storage(":memory:")
        storage.init_schema()
        storage.save_memory(Fact(id="c1", project_id="p", content="first git commit", metadata={"commit_sha": "abc1234000000000000000000000000000000000"}))
        storage.save_memory(Fact(id="c2", project_id="p", content="second git commit", metadata={"commit_sha": "abc1234fffffffffffffffffffffffffffffffff"}))
        result = AssistedRetriever(storage).retrieve("commit abc1234")
        self.assertEqual(result.state, RetrievalState.AMBIGUOUS_CANDIDATES)
        self.assertEqual(result.identifier_constraint_status, "IDENTIFIER_MATCHED_MULTIPLE")
        storage.conn.close()

    def test_14_nonexistent_sha_with_commit_keyword(self) -> None:
        query = "commit dea8b9c7d5e3f0123456789abcdef012345abc"
        result = self.retriever.retrieve(query)
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)
        self.assertEqual(result.identifier_constraint_status, "IDENTIFIER_NOT_FOUND")

    def test_15_nonexistent_sha_with_sha_keyword(self) -> None:
        query = "SHA dea8b9c7d5e3f0123456789abcdef012345abc"
        result = self.retriever.retrieve(query)
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)
        self.assertTrue(result.identifier_constraint_applied)

    def test_15b_nonexistent_seven_character_commit_prefix(self) -> None:
        result = self.retriever.retrieve("commit 7654321")
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)
        self.assertEqual(result.identifier_constraint_status, "IDENTIFIER_NOT_FOUND")

    def test_16_common_hex_without_git_context_is_not_commit_constraint(self) -> None:
        result = self.retriever.retrieve("cor cafe1234 usada na interface")
        self.assertNotIn(
            "commit_sha",
            [m["field"] for m in result.identifier_matches],
        )

    def test_17_existing_protocol(self) -> None:
        result = self.retriever.retrieve("protocolo PROTO-1003")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)
        self.assertEqual(result.top_memory().id, "bio-f3")

    def test_18_nonexistent_protocol_blocks_text_substitution(self) -> None:
        result = self.retriever.retrieve("protocolo PROTO-9999 documentação protocolo")
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)
        self.assertEqual(result.identifier_constraint_status, "IDENTIFIER_NOT_FOUND")

    def test_19_existing_ticket(self) -> None:
        result = self.retriever.retrieve("ticket 1002")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)
        self.assertEqual(result.top_memory().id, "bio-f2")

    def test_20_nonexistent_ticket(self) -> None:
        result = self.retriever.retrieve("ticket 9999 atendimento suporte")
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)

    def test_21_existing_serial(self) -> None:
        result = self.retriever.retrieve("serial SN-ACME-1002")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)
        self.assertEqual(result.top_memory().id, "fleet-eq2")

    def test_22_nonexistent_serial_blocks_similar_text(self) -> None:
        result = self.retriever.retrieve("serial SN-ACME-9999 equipamento ACME")
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)

    def test_23_existing_mac_different_format(self) -> None:
        result = self.retriever.retrieve("MAC AA:BB:CC:DD:EE:02")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)
        self.assertEqual(result.top_memory().id, "fleet-eq2")

    def test_24_nonexistent_mac(self) -> None:
        result = self.retriever.retrieve("MAC AA:BB:CC:DD:EE:99 equipamento")
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)

    def test_25_existing_absolute_path(self) -> None:
        result = self.retriever.retrieve(r"arquivo D:\src\harness\orchestrator.py")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)
        self.assertEqual(result.top_memory().id, "harness-f1")

    def test_26_nonexistent_absolute_path(self) -> None:
        result = self.retriever.retrieve(r"arquivo D:\src\harness\missing.py")
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)

    def test_27_partial_path_unique(self) -> None:
        result = self.retriever.retrieve("orchestrator.py")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)
        self.assertEqual(result.top_memory().id, "harness-f1")

    def test_28_partial_path_multiple(self) -> None:
        result = self.retriever.retrieve("__init__.py")
        self.assertEqual(result.state, RetrievalState.AMBIGUOUS_CANDIDATES)
        self.assertEqual(result.identifier_constraint_status, "IDENTIFIER_MATCHED_MULTIPLE")

    def test_29_pure_text_query_still_works(self) -> None:
        result = self.retriever.retrieve("SQLite backend armazenamento experimental")
        self.assertNotEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)
        self.assertEqual(result.identifier_constraint_status, "NO_EXPLICIT_IDENTIFIER")

    def test_30_true_ambiguity_remains_ambiguous(self) -> None:
        result = self.retriever.retrieve("__init__.py")
        self.assertEqual(result.state, RetrievalState.AMBIGUOUS_CANDIDATES)
        self.assertGreaterEqual(len(result.memories), 2)

    def test_31_true_absence_remains_absent(self) -> None:
        result = self.retriever.retrieve("blockchain smart contracts ethereum")
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)

    def test_32_zero_fake_sources(self) -> None:
        result = self.retriever.retrieve("serial SN-ACME-1002")
        self.assertTrue(result.memories)
        self.assertTrue(all(self.storage.get_memory(m.id) is not None for m in result.memories))


class ArchitecturalReviewRegressionTests(unittest.TestCase):
    def test_clarification_uses_each_candidates_memory_type(self) -> None:
        storage = Storage(":memory:")
        storage.init_schema()
        shared = {
            "project_id": "portable-clarification",
            "content": "shared architectural candidate",
        }
        storage.save_memory(Fact(id="type-fact", **shared))
        storage.save_memory(Decision(id="type-decision", **shared))
        storage.save_memory(Hypothesis(id="type-hypothesis", **shared))
        config = AssistedRetrievalConfig(
            confirmed_min_score=1.0,
            ambiguous_min_score=0.9,
            clarification_min_score=0.01,
            not_found_floor=0.0,
        )

        result = AssistedRetriever(storage, config=config).retrieve(
            "shared architectural candidate"
        )

        self.assertEqual(result.state, RetrievalState.CLARIFICATION_REQUIRED)
        self.assertEqual(result.clarification_dimension, "memory_type")
        self.assertEqual(
            result.clarification_question,
            "Era uma decisão aprovada, um fato verificado ou uma hipótese?",
        )
        storage.conn.close()


class PreservationAndDiagnosticsTests(unittest.TestCase):
    fixture: PortableR41Project

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = PortableR41Project.create()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture.close()

    def test_33_symbol_query_still_works(self) -> None:
        result = AssistedRetriever(self.fixture.storage).retrieve("ClarificationCycle")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)

    def test_34_r3_remains_functional(self) -> None:
        storage = Storage(":memory:")
        storage.init_schema()
        storage.save_memory(Fact(id="r3-f1", project_id="p", content="SQLite armazenamento persistente"))
        result = HybridRetriever(
            storage,
            semantic=DeterministicSemanticAdapter(),
        ).search("SQLite")
        self.assertEqual(result.source_ids, ["r3-f1"])
        storage.conn.close()

    def test_35_json_output_contains_identifier_diagnostics(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--db", str(self.fixture.db_path),
                "search", "commit dea8b9c7d5e3f0123456789abcdef012345abc",
                "--retrieval-mode", "assisted", "--json",
            ],
        )
        self.assertEqual(result.exit_code, 0, result.output)
        payload = json.loads(result.output)
        self.assertTrue(payload["identifier_constraint_applied"])
        self.assertEqual(payload["identifier_constraint_status"], "IDENTIFIER_NOT_FOUND")
        self.assertEqual(payload["identifier_matches"][0]["match_count"], 0)
        self.assertTrue(payload["identifier_failure_reason"])

    def test_36_constraint_enum_is_public(self) -> None:
        self.assertEqual(
            IdentifierConstraintStatus.IDENTIFIER_NOT_FOUND.value,
            "IDENTIFIER_NOT_FOUND",
        )

    def test_37_test_query_literal_is_not_operational_evidence(self) -> None:
        storage = Storage(":memory:")
        storage.init_schema()
        storage.save_memory(Fact(
            id="test-literal",
            project_id="p",
            content="blockchain smart contracts ethereum",
            metadata={"source_path": "tests/test_absence.py"},
        ))
        result = AssistedRetriever(storage).retrieve(
            "blockchain smart contracts ethereum"
        )
        self.assertEqual(result.state, RetrievalState.MEMORY_NOT_FOUND)
        storage.conn.close()

    def test_38_test_source_remains_retrievable_by_explicit_path(self) -> None:
        storage = Storage(":memory:")
        storage.init_schema()
        storage.save_memory(Fact(
            id="test-path",
            project_id="p",
            content="absence regression",
            metadata={
                "source_path": "tests/test_absence.py",
                "file_path": "tests/test_absence.py",
            },
        ))
        result = AssistedRetriever(storage).retrieve("tests/test_absence.py")
        self.assertEqual(result.state, RetrievalState.MEMORY_CONFIRMED)
        self.assertEqual(result.top_memory().id, "test-path")
        storage.conn.close()


if __name__ == "__main__":
    unittest.main()
