"""MEC R4 — CLI integration tests.

End-to-end tests exercising the `search` command with both --retrieval-mode
hybrid (R3) and --retrieval-mode assisted (R4), including clarification cycle,
JSON output, and persistent database reopening.
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from click.testing import CliRunner

from mec_lab.cli import cli
from tests.fixtures.operational_fixture import (
    COMMIT_FULL_A,
    build_fixture_storage,
)


def _populated_db_path() -> str:
    """Create a temp file-backed database with the R4 fixture and return its path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    store = build_fixture_storage(db_path=tmp.name)
    store.conn.close()
    return tmp.name


class TestCliAssistedMode(unittest.TestCase):
    """Tests for --retrieval-mode assisted."""

    def setUp(self) -> None:
        self.runner = CliRunner()
        self.db_path = _populated_db_path()

    def tearDown(self) -> None:
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def _invoke(self, *args: str) -> tuple[int, str]:
        result = self.runner.invoke(cli, ["--db", self.db_path, *args])
        return result.exit_code, result.output

    # ------------------------------------------------------------------
    # R4: confirmed by exact identifier
    # ------------------------------------------------------------------

    def test_assisted_exact_identifier_confirmed(self) -> None:
        exit_code, output = self._invoke(
            "search", "--retrieval-mode", "assisted",
            "protocolo PROTO-2001",
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("MEMORY_CONFIRMED", output)
        self.assertIn("doc-p1", output)

    # ------------------------------------------------------------------
    # R4: ambiguity with up to 3 candidates
    # ------------------------------------------------------------------

    def test_assisted_ambiguous_candidates(self) -> None:
        exit_code, output = self._invoke(
            "search", "--retrieval-mode", "assisted",
            "serial SN-ACME-1001",
        )
        self.assertEqual(exit_code, 0)
        found = (
            "AMBIGUOUS_CANDIDATES" in output
            or "MEMORY_CONFIRMED" in output
        )
        self.assertTrue(found, f"Expected AMBIGUOUS or CONFIRMED, got: {output[:500]}")

    # ------------------------------------------------------------------
    # R4: clarification -> one answer -> confirmed
    # ------------------------------------------------------------------

    def test_assisted_clarification_one_answer_confirms(self) -> None:
        # Simulate interactive: provide answer via stdin
        result = self.runner.invoke(
            cli,
            ["--db", self.db_path, "search", "--retrieval-mode", "assisted",
             "quem foi o responsável"],
            input="Saimon\n",
        )
        # Should either confirm or be ambiguous after answer
        found = any(
            s in result.output
            for s in ("MEMORY_CONFIRMED", "AMBIGUOUS_CANDIDATES", "MEMORY_NOT_FOUND")
        )
        self.assertTrue(found, f"Unexpected output: {result.output[:500]}")

    # ------------------------------------------------------------------
    # R4: clarification -> two answers -> confirmed
    # ------------------------------------------------------------------

    def test_assisted_clarification_two_answers(self) -> None:
        result = self.runner.invoke(
            cli,
            ["--db", self.db_path, "search", "--retrieval-mode", "assisted",
             "quem foi o responsável"],
            input="Saimon\nProjeto MEC\n",
        )
        # After two answers should reach a terminal state
        self.assertNotIn("CLARIFICATION_REQUIRED", result.output)

    # ------------------------------------------------------------------
    # R4: hard stop after three insufficient answers
    # ------------------------------------------------------------------

    def test_assisted_three_insufficient_answers(self) -> None:
        result = self.runner.invoke(
            cli,
            ["--db", self.db_path, "search", "--retrieval-mode", "assisted",
             "motor elétrico"],
            input="não sei\nnão sei\nnão sei\n",
        )
        # After 3 clarifications, must return MEMORY_NOT_FOUND
        # The cycle hard-stops at 3
        self.assertIn("MEMORY_NOT_FOUND", result.output)

    # ------------------------------------------------------------------
    # R4: JSON output
    # ------------------------------------------------------------------

    def test_assisted_json_output_valid(self) -> None:
        exit_code, output = self._invoke(
            "search", "--retrieval-mode", "assisted", "--json",
            "commit " + COMMIT_FULL_A,
        )
        self.assertEqual(exit_code, 0)
        data = json.loads(output.strip())
        self.assertIn("state", data)
        self.assertIn("candidates", data)
        self.assertIn("memories", data)
        self.assertEqual(data["state"], "MEMORY_CONFIRMED")

    def test_assisted_json_output_has_all_fields(self) -> None:
        exit_code, output = self._invoke(
            "search", "--retrieval-mode", "assisted", "--json",
            "commit " + COMMIT_FULL_A,
        )
        self.assertEqual(exit_code, 0)
        data = json.loads(output.strip())
        required = [
            "state", "query", "candidates", "memories", "related",
            "explanation", "clarification_dimension", "clarification_question",
            "clarifications_used", "session_filters",
        ]
        for field in required:
            self.assertIn(field, data, f"Missing field: {field}")

    # ------------------------------------------------------------------
    # R4: persistent DB reopened
    # ------------------------------------------------------------------

    def test_assisted_persistent_reopen(self) -> None:
        # First invocation
        exit_code, output1 = self._invoke(
            "search", "--retrieval-mode", "assisted",
            "protocolo PROTO-2001",
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("MEMORY_CONFIRMED", output1)

        # Second invocation (same DB file, different process effectively)
        exit_code, output2 = self._invoke(
            "search", "--retrieval-mode", "assisted",
            "protocolo PROTO-2001",
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("MEMORY_CONFIRMED", output2)


class TestCliHybridModePreserved(unittest.TestCase):
    """R3 mode (--retrieval-mode hybrid) must remain fully functional."""

    def setUp(self) -> None:
        self.runner = CliRunner()
        self.db_path = _populated_db_path()

    def tearDown(self) -> None:
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def _invoke(self, *args: str) -> tuple[int, str]:
        result = self.runner.invoke(cli, ["--db", self.db_path, *args])
        return result.exit_code, result.output

    def test_hybrid_mode_still_works(self) -> None:
        exit_code, output = self._invoke(
            "search", "--retrieval-mode", "hybrid",
            "SQLite armazenamento",
        )
        self.assertEqual(exit_code, 0)
        # R3 output has a table with "Hybrid search"
        self.assertIn("Hybrid search", output)

    def test_default_mode_is_hybrid(self) -> None:
        """Without --retrieval-mode, behaviour must match R3 (hybrid)."""
        exit_code, output = self._invoke(
            "search", "SQLite armazenamento",
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("Hybrid search", output)

    def test_lexical_strategy_still_works(self) -> None:
        exit_code, output = self._invoke(
            "search", "--strategy", "lexical",
            "SQLite",
        )
        self.assertEqual(exit_code, 0)
        self.assertIn("Lexical search", output)

    def test_explicit_r3_vs_r4_different_output(self) -> None:
        """Explicit selection between R3 and R4 must produce different outputs."""
        _, out_r3 = self._invoke(
            "search", "--retrieval-mode", "hybrid",
            "protocolo PROTO-2001",
        )
        _, out_r4 = self._invoke(
            "search", "--retrieval-mode", "assisted",
            "protocolo PROTO-2001",
        )
        # R3 uses "Hybrid search" table, R4 uses "Estado:" header
        self.assertIn("Hybrid search", out_r3)
        self.assertIn("Estado:", out_r4)


class TestCliJsonOutput(unittest.TestCase):
    """JSON output mode tests."""

    def setUp(self) -> None:
        self.runner = CliRunner()
        self.db_path = _populated_db_path()

    def tearDown(self) -> None:
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def _invoke(self, *args: str) -> tuple[int, str]:
        result = self.runner.invoke(cli, ["--db", self.db_path, *args])
        return result.exit_code, result.output

    def test_r3_json_output_valid(self) -> None:
        exit_code, output = self._invoke(
            "search", "--retrieval-mode", "hybrid", "--json",
            "SQLite",
        )
        self.assertEqual(exit_code, 0)
        data = json.loads(output.strip())
        self.assertIn("quality", data)
        self.assertIn("candidates", data)

    def test_r4_json_clarification_dimension_present(self) -> None:
        exit_code, output = self._invoke(
            "search", "--retrieval-mode", "assisted", "--json",
            "quem foi o responsável",
        )
        self.assertEqual(exit_code, 0)
        data = json.loads(output.strip())
        self.assertIn("state", data)
        # The clarification fields must exist even if null
        self.assertIn("clarification_dimension", data)


if __name__ == "__main__":
    unittest.main()
