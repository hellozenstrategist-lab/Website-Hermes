import json
import tempfile
from pathlib import Path
import unittest

from ops_cfo.engine import OpsCFOAgent, StaticStripeGateway


class OpsCFOAgentTests(unittest.TestCase):
    def test_demo_goal_creates_revenue_link_budgeted_spend_and_blocks_large_purchase(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger_path = Path(tmp) / "ledger.json"
            agent = OpsCFOAgent(
                stripe=StaticStripeGateway(base_url="https://stripe.test"),
                ledger_path=ledger_path,
            )

            state = agent.run_goal(
                goal="Launch paid AI security review service",
                budget_usd=250,
                customer_offer_usd=499,
            )

            self.assertEqual(state["goal"], "Launch paid AI security review service")
            self.assertEqual(state["budget_usd"], 250)
            self.assertEqual(state["revenue"]["amount_usd"], 499)
            self.assertEqual(state["revenue"]["payment_link"], "https://stripe.test/pay/ai-security-review-499")
            self.assertEqual(state["spend"]["approved_total_usd"], 42)
            self.assertEqual(state["spend"]["blocked_total_usd"], 200)
            self.assertEqual(state["unit_economics"]["projected_margin_usd"], 457)
            self.assertEqual(state["unit_economics"]["gross_margin_percent"], 91.58)
            self.assertEqual(state["next_action"], "Record 1-3 minute demo and submit to Nous Discord + Typeform")
            blocked_names = [item["name"] for item in state["spend"]["items"] if item["status"] == "BLOCKED_APPROVAL_REQUIRED"]
            self.assertEqual(blocked_names, ["GPU inference credits"])
            self.assertTrue(any(event["type"] == "approval_gate" for event in state["audit_trail"]))

            persisted = json.loads(ledger_path.read_text())
            self.assertEqual(persisted, state)

    def test_approving_blocked_purchase_updates_spend_and_audit_trail_without_exceeding_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = OpsCFOAgent(
                stripe=StaticStripeGateway(base_url="https://stripe.test"),
                ledger_path=Path(tmp) / "ledger.json",
            )
            agent.run_goal("Launch paid AI security review service", budget_usd=250, customer_offer_usd=499)

            state = agent.approve_spend("GPU inference credits")

            self.assertEqual(state["spend"]["approved_total_usd"], 242)
            self.assertEqual(state["spend"]["blocked_total_usd"], 0)
            self.assertEqual(state["unit_economics"]["projected_margin_usd"], 257)
            self.assertTrue(any(event["type"] == "human_approval" for event in state["audit_trail"]))

    def test_approval_refuses_to_exceed_budget_cap(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = OpsCFOAgent(
                stripe=StaticStripeGateway(base_url="https://stripe.test"),
                ledger_path=Path(tmp) / "ledger.json",
            )
            agent.run_goal("Launch paid AI security review service", budget_usd=100, customer_offer_usd=499)

            with self.assertRaisesRegex(ValueError, "exceed budget"):
                agent.approve_spend("GPU inference credits")


if __name__ == "__main__":
    unittest.main()
