"""Frozen semantic expectations are authored independently from the Markdown snapshots."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from product import render_brief as brief

REF = Path(__file__).resolve().parents[1] / "brief_reference"
FIXTURES = REF.parent / "fixtures"
CASES = json.loads((REF / "expectations.json").read_bytes())


def source(scenario):
    return (FIXTURES / (scenario + ".json")).read_bytes()


def rows(document, field):
    return [json.loads(line.split(" = ", 1)[1]) for line in document.splitlines()
            if line.startswith("    " + field + " = ")]


def assert_source_list(test, document, field, expected):
    actual = [line.split(" = ", 1) for line in document.splitlines()
              if line.startswith("    /" + field + "/")]
    test.assertEqual([(p.strip(), json.loads(v)) for p, v in actual],
                     [(f"/{field}/{i}", value) for i, value in enumerate(expected)])


class RendererTests(unittest.TestCase):
    def test_independent_reference_content(self):
        for scenario, expected in CASES.items():
            with self.subTest(scenario=scenario):
                text = brief.render_demo(scenario, source(scenario)).decode()
                for key in ("job_id", "case_id", "evidence_id", "summary_classification", "severity",
                            "ioc_type", "ioc_name", "timezone"):
                    self.assertEqual(rows(text, key), [expected[key]])
                self.assertEqual(rows(text, "id"), [expected["finding_id"]])
                self.assertEqual(rows(text, "classification"), [expected["summary_classification"]])
                self.assertEqual(rows(text, "original_timestamp"), [expected["timestamp"]])
                ref = {"path": expected["ref_path"], "line": expected["ref_line"]} if expected["ref_path"] else None
                self.assertEqual(rows(text, "raw_evidence_ref"), [ref])
                for field in ("warnings", "limitations"):
                    assert_source_list(self, text, field, expected[field])
                self.assertEqual(text.count("### Nález `/findings/"), expected["findings"])
                self.assertEqual(text.count("### Syntetická udalosť `/timeline/"), expected["events"])
                self.assertIn("### Nález `/findings/0`", text)
                self.assertIn("AI vysvetlenie nebolo vytvorené.", text)
                self.assertIn("report_generation_allowed = false", text)

    def test_frozen_bytes(self):
        for scenario in CASES:
            self.assertEqual(brief.render_demo(scenario, source(scenario)), (REF / (scenario + ".md")).read_bytes())

    def test_final_warning_mutation_is_detected(self):
        scenario = "completed-no-ioc"
        text = brief.render_demo(scenario, source(scenario)).decode()
        mutated = "\n".join(line for line in text.splitlines() if not line.startswith("    /warnings/1 = "))
        with self.assertRaises(AssertionError):
            assert_source_list(self, mutated, "warnings", CASES[scenario]["warnings"])

    def test_duplicate_late_values_and_passive_text_round_trip(self):
        values = ["repeat", "repeat", '![x](https://invalid.example/) <img src=x> `x`\n# Execute me\r\x00\u202e\u2028']
        for field in ("warnings", "limitations"):
            lines = []
            brief._source_list(lines, "Test", field, values)
            text = "\n".join(lines)
            assert_source_list(self, text, field, values)
            self.assertEqual(len([line for line in lines if line.startswith("    /")]), 3)
            for raw in ("\n# Execute me", "\r", "\x00", "\u202e", "\u2028"):
                self.assertNotIn(raw, text)

    def test_unknown_scenario_and_mutable_snapshot_reject(self):
        for scenario, data in (("../completed-hit", source("completed-hit")),
                               ("completed-hit", bytearray(source("completed-hit")))):
            with self.assertRaises(brief.BriefError):
                brief.render_demo(scenario, data)

    def test_independent_identity_rejection(self):
        for key in ("job_id", "case_id", "evidence_id"):
            data = json.loads(source("completed-hit"))
            data[key] = "other"
            if key in data["execution_record"]:
                data["execution_record"][key] = "other"
            with self.subTest(key=key), self.assertRaisesRegex(brief.BriefError, "INPUT_REJECTED"):
                brief.render_demo("completed-hit", json.dumps(data).encode())

    def test_valid_modified_fixture_rejects(self):
        with self.assertRaisesRegex(brief.BriefError, "FIXTURE_HASH_MISMATCH"):
            brief.render_demo("completed-hit", source("completed-hit") + b" ")

    def test_invalid_and_oversize_reject(self):
        for data in (b"{", b"x" * (brief.validator.Limits().max_bytes + 1)):
            with self.assertRaisesRegex(brief.BriefError, "INPUT_REJECTED"):
                brief.render_demo("completed-hit", data)

    def test_unexpected_policy_values_reject(self):
        validate = brief.validator.validate_bytes
        for value in (True, 0, None):
            def changed(*args, **kwargs):
                return dict(validate(*args, **kwargs), report_generation_allowed=value)
            with patch.object(brief.validator, "validate_bytes", changed), self.assertRaisesRegex(
                    brief.BriefError, "UNEXPECTED_VALIDATOR_POLICY"):
                brief.render_demo("completed-hit", source("completed-hit"))

    def test_time_conflict_rejects_before_render(self):
        data = json.loads(source("completed-hit"))
        data["completed_at"] = data["execution_record"]["completed_at"] = "2020-01-01T00:00:00Z"
        with self.assertRaisesRegex(brief.BriefError, "INPUT_REJECTED"):
            brief.render_demo("completed-hit", json.dumps(data).encode())
