import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from agentic_inference_refunds.cli import main  # noqa: E402
from agentic_inference_refunds.claim import build_claim, render_markdown  # noqa: E402
from agentic_inference_refunds.rates import RateBook, normalize_model  # noqa: E402
from agentic_inference_refunds.records import SourceResult, UsageRecord, redact  # noqa: E402
from agentic_inference_refunds.scope import load_scope, validate_scope  # noqa: E402
from agentic_inference_refunds.sources import claude_code, codex, copilot, generic  # noqa: E402

FX = ROOT / "tests" / "fixtures"


class ClaudeCodeTests(unittest.TestCase):
    def setUp(self):
        self.res = claude_code.load(FX / "claude" / "sess-1.jsonl")

    def test_dedupes_streamed_messages_and_reads_subagents(self):
        ids = sorted(r.request_id for r in self.res.records)
        self.assertEqual(ids, ["msg_1", "msg_2", "msg_3", "msg_s1"])
        sub = next(r for r in self.res.records if r.request_id == "msg_s1")
        self.assertEqual(sub.group, "wf_test")
        self.assertEqual(sub.agent_label, "lens:test")
        self.assertEqual(sub.agent_id, "x1")

    def test_splits_cache_writes_by_ttl(self):
        m1 = next(r for r in self.res.records if r.request_id == "msg_1")
        self.assertEqual((m1.input_tokens, m1.cache_read_tokens, m1.cache_write_1h_tokens, m1.cache_write_5m_tokens), (10, 1000, 2000, 0))
        self.assertEqual((m1.output_tokens, m1.reasoning_tokens), (100, 40))

    def test_human_turns_skip_tool_results_and_notifications(self):
        self.assertEqual([t.timestamp for t in self.res.human_turns], ["2026-01-01T10:00:00.000Z", "2026-01-01T11:00:00.000Z"])

    def test_without_subagents(self):
        res = claude_code.load(FX / "claude" / "sess-1.jsonl", include_subagents=False)
        self.assertEqual(len(res.records), 3)


class CodexTests(unittest.TestCase):
    def test_token_usage_records(self):
        res = codex.load(FX / "codex" / "rollout-a.jsonl")
        self.assertEqual(len(res.records), 2)
        r1 = next(r for r in res.records if r.request_id == "r1")
        self.assertEqual((r1.input_tokens, r1.cache_read_tokens, r1.cache_write_tokens, r1.output_tokens, r1.reasoning_tokens), (1000, 8000, 1000, 500, 300))
        self.assertEqual(r1.model, "gpt-6.1-sol")
        self.assertEqual(r1.agent_id, "main")
        r2 = next(r for r in res.records if r.request_id == "r2")
        self.assertEqual(r2.agent_id, "thread-sub")
        self.assertEqual(len(res.human_turns), 1)

    def test_cumulative_fallback(self):
        res = codex.load(FX / "codex" / "rollout-old.jsonl")
        self.assertEqual(len(res.records), 2)
        second = res.records[1]
        self.assertEqual((second.input_tokens, second.cache_read_tokens, second.output_tokens, second.reasoning_tokens), (500, 1500, 200, 50))
        self.assertTrue(res.warnings)


class CopilotTests(unittest.TestCase):
    def setUp(self):
        self.res = copilot.load(FX / "copilot" / "sess-c1")

    def test_records_and_dedupe(self):
        self.assertEqual(len(self.res.records), 3)
        opus = next(r for r in self.res.records if r.model == "claude-opus-5.5")
        self.assertEqual((opus.input_tokens, opus.cache_read_tokens, opus.cache_write_tokens), (500, 3000, 1500))

    def test_premium_requests_only_for_user_calls(self):
        units = sum(r.provider_units.get("premium_requests", 0) for r in self.res.records)
        self.assertEqual(units, 15.0)
        self.assertEqual(self.res.provider_totals[0]["total_premium_request_cost"], 15.0)

    def test_session_state_root(self):
        res = copilot.load(FX / "copilot")
        self.assertEqual(len(res.records), 3)


class PricingTests(unittest.TestCase):
    def setUp(self):
        self.book = RateBook.load()

    def test_normalize(self):
        self.assertEqual(normalize_model("claude-opus-5.5"), normalize_model("claude-opus-5-5"))
        self.assertIsNotNone(self.book.lookup("anthropic/claude-opus-5.5"))

    def test_opus_price_exact(self):
        r = UsageRecord(tool="t", provider="anthropic", model="claude-opus-5-5", timestamp="2026-01-01T00:00:00Z",
                        input_tokens=1_000_000, cache_read_tokens=1_000_000, cache_write_5m_tokens=1_000_000,
                        cache_write_1h_tokens=1_000_000, output_tokens=1_000_000)
        p = self.book.price(r)
        self.assertAlmostEqual(p["total"], 4 + 0.2 + 5 + 8 + 20)

    def test_unknown_ttl_priced_at_5m(self):
        r = UsageRecord(tool="t", provider="anthropic", model="claude-opus-5-5", timestamp="2026-01-01T00:00:00Z", cache_write_tokens=1_000_000)
        self.assertAlmostEqual(self.book.price(r)["total"], 5.0)

    def test_unknown_model_is_unpriced(self):
        r = UsageRecord(tool="t", provider="x", model="mystery-model", timestamp="2026-01-01T00:00:00Z", output_tokens=10)
        self.assertFalse(self.book.price(r)["priced"])

    def test_override_card(self):
        with tempfile.TemporaryDirectory() as d:
            card = Path(d) / "c.json"
            card.write_text(json.dumps({"id": "mine", "provider": "x", "verified": True, "models": {"mystery-model": {"input": 1, "output": 2, "cache_read": 0.1, "cache_write_5m": 1, "cache_write_1h": 1}}}))
            book = RateBook.load([card])
            self.assertTrue(book.price(UsageRecord(tool="t", provider="x", model="mystery-model", timestamp="2026-01-01T00:00:00Z", output_tokens=1_000_000))["priced"])


class ClaimTests(unittest.TestCase):
    def setUp(self):
        self.scope = load_scope(FX / "scope-fixture.toml")
        self.src = claude_code.load(FX / "claude" / "sess-1.jsonl")
        self.claim = build_claim(self.scope, self.src, RateBook.load())

    def test_segments_and_refund(self):
        segs = {s["name"]: s for s in self.claim["segments"]}
        self.assertEqual(segs["Lens work"]["requests"], 1)
        self.assertEqual(segs["Main thread before the objection"]["requests"], 2)
        self.assertEqual(segs["After the objection"]["requests"], 1)
        # 0.047008 + 0.01824 + 0.00862 = 0.073868
        self.assertEqual(self.claim["remedy_request"]["amount_usd"], 0.07)
        self.assertEqual(self.claim["totals"]["unclassified"]["requests"], 0)

    def test_comparison_and_behavior(self):
        b = self.claim["behavior"]
        self.assertEqual(b["subagents_total"], 1)
        self.assertEqual(b["human_turns"], 2)
        self.assertEqual(b["before_first_objection"]["requests"], 3)
        self.assertIn("largest_spend_between_human_messages", b)

    def test_markdown(self):
        md = render_markdown(self.claim)
        self.assertIn("Requested remedy", md)
        self.assertIn("Test lens", md)

    def test_unclassified_is_reported_not_refunded(self):
        scope = dict(self.scope, segments=[{"name": "only lens", "status": "out_of_scope", "match": {"groups": ["wf_*"]}}])
        claim = build_claim(scope, self.src, RateBook.load())
        self.assertEqual(claim["totals"]["unclassified"]["requests"], 3)
        self.assertTrue(any("matched no segment" in w for w in claim["warnings"]))

    def test_validation(self):
        with self.assertRaises(ValueError):
            validate_scope({"segments": [{"status": "nope"}]})

    def test_redact(self):
        red = redact(self.src)
        self.assertTrue(all(r.session_id.startswith("s-") for r in red.records))
        self.assertTrue(all("/" not in f["path"] for f in red.files))


class CliTests(unittest.TestCase):
    def test_claim_both_formats(self):
        with tempfile.TemporaryDirectory() as d:
            rc = main(["claim", "--scope", str(FX / "scope-fixture.toml"), "--claude-code", str(FX / "claude" / "sess-1.jsonl"), "--format", "both", "--out-dir", d])
            self.assertEqual(rc, 0)
            data = json.loads((Path(d) / "claim.json").read_text())
            self.assertEqual(data["schema"], "agentic-inference-refunds/claim@1")
            self.assertTrue((Path(d) / "claim.md").exists())

    def test_usage_roundtrip_through_generic(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "u.jsonl"
            self.assertEqual(main(["usage", "--claude-code", str(FX / "claude" / "sess-1.jsonl"), "--codex", str(FX / "codex"), "--out", str(out)]), 0)
            res = generic.load(out)
            self.assertEqual(len(res.records), 4 + 4)
            self.assertEqual(len(res.human_turns), 2 + 1)

    def test_strict_exit_code_on_unpriced(self):
        with tempfile.TemporaryDirectory() as d:
            scope = Path(d) / "s.json"
            scope.write_text(json.dumps({"requested": {"summary": "x"}, "segments": [{"name": "all", "status": "out_of_scope"}]}))
            rc = main(["claim", "--scope", str(scope), "--copilot", str(FX / "copilot"), "--format", "json", "--out-dir", d, "--strict"])
            self.assertEqual(rc, 3)

    def test_init_and_schema(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "scope.toml"
            self.assertEqual(main(["init", "--out", str(out)]), 0)
            self.assertIn("[requested]", out.read_text())
        self.assertEqual(main(["schema", "claim"]), 0)


class ExampleRegressionTests(unittest.TestCase):
    """The worked example in examples/ must keep producing the published figures."""

    EX = ROOT / "examples" / "2026-11-15-wrong-scope-config-gap-analysis"

    @unittest.skipUnless((ROOT / "examples" / "2026-11-15-wrong-scope-config-gap-analysis" / "usage.jsonl").exists(), "example data not present")
    def test_example_claim_total(self):
        expected = json.loads((self.EX / "expected.json").read_text())
        claim = build_claim(load_scope(self.EX / "scope.toml"), generic.load(self.EX / "usage.jsonl"), RateBook.load())
        self.assertEqual(claim["remedy_request"]["amount_usd"], expected["refundable_usd"])
        self.assertEqual(claim["comparison"]["cost_of_approved_scope_usd"], expected["approved_usd"])
        self.assertEqual(claim["totals"]["refundable"]["requests"], expected["refundable_requests"])


if __name__ == "__main__":
    unittest.main()
