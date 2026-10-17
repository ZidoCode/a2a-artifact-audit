"""Tests for a2a-artifact-audit — deterministic, no network."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import a2a_artifact_audit as aa


def ev(aid="a1", text="chunk", append=True, last=False):
    return {"jsonrpc": "2.0", "id": 1, "result": {
        "kind": "artifact-update", "taskId": "t1", "contextId": "c1",
        "append": append, "last_chunk": last,
        "artifact": {"artifactId": aid, "parts": [{"kind": "text", "text": text}]}}}


def sev(findings, level):
    return [m for s, m in findings if s == level]


class TestAudit(unittest.TestCase):
    def test_clean_stream(self):
        findings, arts = aa.audit([ev(append=False), ev(last=True)])
        self.assertEqual(sev(findings, "CRITICAL"), [])
        self.assertTrue(arts["a1"]["closed"])

    def test_write_after_close_critical(self):
        findings, _ = aa.audit([ev(append=False, last=True), ev(append=True)])
        crit = sev(findings, "CRITICAL")
        self.assertEqual(len(crit), 1)
        self.assertIn("after last_chunk", crit[0])

    def test_duplicate_part_warning(self):
        findings, _ = aa.audit([ev(append=False), ev(append=True, text="chunk2"),
                                ev(append=True, text="chunk2", last=True)])
        self.assertEqual(len(sev(findings, "WARNING")), 1)
        self.assertIn("duplicate", sev(findings, "WARNING")[0])

    def test_first_chunk_append_is_info(self):
        findings, _ = aa.audit([ev(append=True, last=True)])
        self.assertEqual(sev(findings, "INFO"), [sev(findings, "INFO")[0]])
        self.assertIn("append=true", sev(findings, "INFO")[0])
        self.assertEqual(sev(findings, "CRITICAL"), [])

    def test_unclosed_artifact_warning(self):
        findings, _ = aa.audit([ev(append=False)])
        self.assertEqual(len(sev(findings, "WARNING")), 1)
        self.assertIn("never closed", sev(findings, "WARNING")[0])

    def test_wholesale_replace_info(self):
        findings, _ = aa.audit([ev(append=False), ev(append=False, last=True)])
        self.assertTrue(any("replaced wholesale" in m for m in sev(findings, "INFO")))

    def test_no_artifact_id_warning(self):
        e = ev()
        e["result"]["artifact"] = {}
        findings, _ = aa.audit([e])
        self.assertTrue(any("without artifactId" in m for m in sev(findings, "WARNING")))

    def test_size_accounting(self):
        _, arts = aa.audit([ev(append=False), ev(text="bigger chunk payload here", append=True, last=True)])
        self.assertEqual(arts["a1"]["chunks"], 2)
        self.assertGreater(arts["a1"]["parts_tokens"], 0)


class TestReport(unittest.TestCase):
    def test_clean_report(self):
        out = aa.report([ev(append=False), ev(append=True, text="chunk2", last=True)])
        self.assertIn("clean", out)

    def test_critical_verdict(self):
        out = aa.report([ev(append=False, last=True), ev(append=True)])
        self.assertIn("CRITICAL", out)
        self.assertIn("silently lost", out)

    def test_shows_open_artifacts(self):
        out = aa.report([ev(append=False)])
        self.assertIn("OPEN", out)


class TestSimulate(unittest.TestCase):
    def setUp(self):
        self.card = {"name": "x", "description": "y" * 40, "skills": []}

    def test_more_chunks_more_tokens(self):
        a = aa.simulate(self.card, artifacts=1, chunks=2)
        b = aa.simulate(self.card, artifacts=1, chunks=10)
        self.assertGreater(b["tokens_total"], a["tokens_total"])

    def test_no_gap_zero_findings(self):
        m = aa.simulate(self.card, artifacts=2, chunks=3, gap=False)
        self.assertEqual(m["simulated_findings"], 0)

    def test_breaks_down(self):
        m = aa.simulate(self.card, artifacts=2, chunks=3)
        self.assertEqual(m["artifact_events"], 6)
        self.assertEqual(m["tokens_total"], m["per_event_tokens"] * 6)


class TestExitCodes(unittest.TestCase):
    def test_audit_exit_critical(self):
        import subprocess
        p = "/tmp/aa_crit.jsonl"
        with open(p, "w") as f:
            f.write(json.dumps(ev(append=False, last=True)) + "\n" + json.dumps(ev(append=True)) + "\n")
        r = subprocess.run(["python3", "a2a_artifact_audit.py", "audit", p],
                           capture_output=True, text=True,
                           cwd=os.path.dirname(os.path.abspath(__file__)))
        self.assertEqual(r.returncode, 2)

    def test_audit_exit_clean(self):
        import subprocess
        p = "/tmp/aa_ok.jsonl"
        with open(p, "w") as f:
            f.write(json.dumps(ev(append=False)) + "\n" + json.dumps(ev(append=True, last=True)) + "\n")
        r = subprocess.run(["python3", "a2a_artifact_audit.py", "audit", p],
                           capture_output=True, text=True,
                           cwd=os.path.dirname(os.path.abspath(__file__)))
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
