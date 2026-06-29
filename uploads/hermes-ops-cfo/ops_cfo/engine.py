from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


USD = "usd"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def money(value: float | int) -> int:
    if value < 0:
        raise ValueError("Money values must be non-negative")
    if int(value) != value:
        raise ValueError("This prototype accepts whole-dollar USD amounts only")
    return int(value)


class StaticStripeGateway:
    """Deterministic Stripe-like gateway for demos without secrets.

    It intentionally creates no external side effects. The returned URLs are
    stable so the 1-3 minute hackathon demo is reliable on any laptop.
    """

    def __init__(self, base_url: str = "https://stripe.test") -> None:
        self.base_url = base_url.rstrip("/")

    def create_payment_link(
        self,
        product_name: str,
        amount_usd: int,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        amount = money(amount_usd)
        slug = slugify(product_name)
        return {
            "id": f"plink_demo_{slug}_{amount}",
            "url": f"{self.base_url}/pay/{slug}-{amount}",
            "mode": "demo",
            "provider": "stripe-test-double",
            "product_name": product_name,
            "amount_usd": amount,
            "currency": USD,
            "metadata": metadata or {},
        }


class LiveStripeGateway:
    """Minimal Stripe test-mode Payment Link client using only stdlib.

    Safety: from_env refuses live secret keys. This class expects a Stripe test
    key and creates real Stripe test-mode Product, Price, and Payment Link
    objects if STRIPE_SECRET_KEY is configured.
    """

    def __init__(self, secret_key: str) -> None:
        if secret_key.startswith("sk_live_") or secret_key.startswith("rk_live_"):
            raise ValueError("Refusing live Stripe key; use a test key for this hackathon demo")
        if not (secret_key.startswith("sk_test_") or secret_key.startswith("rk_test_")):
            raise ValueError("STRIPE_SECRET_KEY must be a Stripe test key starting sk_test_ or rk_test_")
        self.secret_key = secret_key

    def _post(self, endpoint: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        encoded = urllib.parse.urlencode(fields, doseq=True).encode()
        request = urllib.request.Request(
            f"https://api.stripe.com/v1/{endpoint.lstrip('/')}",
            data=encoded,
            headers={
                "Authorization": f"Bearer {self.secret_key}",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "hermes-ops-cfo-hackathon/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise RuntimeError(f"Stripe API error {exc.code}: {body}") from exc

    def create_payment_link(
        self,
        product_name: str,
        amount_usd: int,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        amount = money(amount_usd)
        product = self._post("products", {"name": product_name})
        price = self._post(
            "prices",
            {
                "product": product["id"],
                "currency": USD,
                "unit_amount": amount * 100,
            },
        )
        fields: Dict[str, Any] = {
            "line_items[0][price]": price["id"],
            "line_items[0][quantity]": 1,
        }
        for key, value in (metadata or {}).items():
            fields[f"metadata[{key}]"] = value
        link = self._post("payment_links", fields)
        return {
            "id": link["id"],
            "url": link["url"],
            "mode": "stripe_test",
            "provider": "stripe",
            "product_name": product_name,
            "amount_usd": amount,
            "currency": USD,
            "metadata": metadata or {},
        }


class StripeGateway:
    @staticmethod
    def from_env() -> StaticStripeGateway | LiveStripeGateway:
        secret_key = os.environ.get("STRIPE_SECRET_KEY", "").strip()
        if not secret_key:
            return StaticStripeGateway()
        if secret_key.startswith("sk_live_") or secret_key.startswith("rk_live_"):
            raise ValueError("Refusing live Stripe key; use a test key for this hackathon demo")
        return LiveStripeGateway(secret_key)


class OpsCFOAgent:
    """Business-ops CFO agent: earns, spends, gates risk, logs audit trail."""

    def __init__(
        self,
        stripe: StaticStripeGateway | LiveStripeGateway,
        ledger_path: str | Path = "ledger.json",
        auto_approve_cap_usd: int = 50,
    ) -> None:
        self.stripe = stripe
        self.ledger_path = Path(ledger_path)
        self.auto_approve_cap_usd = money(auto_approve_cap_usd)

    def run_goal(self, goal: str, budget_usd: int, customer_offer_usd: int = 499) -> Dict[str, Any]:
        budget = money(budget_usd)
        offer = money(customer_offer_usd)
        if not goal.strip():
            raise ValueError("Goal is required")
        if budget == 0:
            raise ValueError("Budget must be greater than zero")
        if offer == 0:
            raise ValueError("Customer offer must be greater than zero")

        audit_trail: List[Dict[str, Any]] = []
        created_at = now_iso()
        revenue_link = self.stripe.create_payment_link(
            "AI Security Review",
            offer,
            metadata={"purpose": "customer_revenue", "agent": "hermes-ops-cfo"},
        )
        audit_trail.append(
            {
                "at": created_at,
                "type": "revenue_link_created",
                "summary": f"Created ${offer} customer payment link",
                "url": revenue_link["url"],
            }
        )

        spend_items = self._build_spend_plan(goal)
        approved_running_total = 0
        for item in spend_items:
            amount = item["amount_usd"]
            if approved_running_total + amount > budget:
                item["status"] = "BLOCKED_BUDGET_CAP"
                item["payment_link"] = None
                item["decision"] = "Would exceed budget cap"
                audit_trail.append(
                    {
                        "at": now_iso(),
                        "type": "budget_gate",
                        "summary": f"Blocked {item['name']} because ${approved_running_total + amount} > ${budget}",
                    }
                )
            elif amount > self.auto_approve_cap_usd:
                item["status"] = "BLOCKED_APPROVAL_REQUIRED"
                item["payment_link"] = None
                item["decision"] = f"Above auto-approval cap (${self.auto_approve_cap_usd})"
                audit_trail.append(
                    {
                        "at": now_iso(),
                        "type": "approval_gate",
                        "summary": f"Blocked {item['name']} pending human approval",
                    }
                )
            else:
                link = self.stripe.create_payment_link(
                    f"Vendor spend: {item['name']}",
                    amount,
                    metadata={"purpose": "vendor_spend", "agent": "hermes-ops-cfo"},
                )
                approved_running_total += amount
                item["status"] = "APPROVED_AUTO"
                item["payment_link"] = link["url"]
                item["decision"] = "Within budget and auto-approval cap"
                audit_trail.append(
                    {
                        "at": now_iso(),
                        "type": "spend_auto_approved",
                        "summary": f"Approved {item['name']} for ${amount}",
                        "url": link["url"],
                    }
                )

        state = {
            "app": "Hermes Ops CFO",
            "created_at": created_at,
            "goal": goal.strip(),
            "budget_usd": budget,
            "auto_approve_cap_usd": self.auto_approve_cap_usd,
            "revenue": {
                "product": "AI Security Review",
                "amount_usd": offer,
                "payment_link": revenue_link["url"],
                "payment_link_id": revenue_link["id"],
                "mode": revenue_link["mode"],
            },
            "spend": {
                "items": spend_items,
            },
            "ops": self._build_ops_plan(),
            "risk_controls": [
                "Live Stripe keys refused; demo/test mode only",
                "No spend above auto-approval cap without human approval",
                "No approval can exceed budget cap",
                "Every revenue/spend decision is written to ledger.json",
            ],
            "next_action": "Record 1-3 minute demo and submit to Nous Discord + Typeform",
            "audit_trail": audit_trail,
        }
        self._recompute(state)
        self._save(state)
        return state

    def approve_spend(self, item_name: str) -> Dict[str, Any]:
        state = self._load()
        if not state:
            raise ValueError("No ledger exists. Run a goal first.")
        normalized = item_name.strip().lower()
        target: Optional[Dict[str, Any]] = None
        for item in state["spend"]["items"]:
            if item["name"].lower() == normalized:
                target = item
                break
        if target is None:
            raise ValueError(f"Unknown spend item: {item_name}")
        if target["status"].startswith("APPROVED"):
            return state

        approved_total = state["spend"]["approved_total_usd"]
        new_total = approved_total + target["amount_usd"]
        if new_total > state["budget_usd"]:
            raise ValueError(
                f"Cannot approve {target['name']}: would exceed budget (${new_total} > ${state['budget_usd']})"
            )

        link = self.stripe.create_payment_link(
            f"Vendor spend: {target['name']}",
            target["amount_usd"],
            metadata={"purpose": "vendor_spend_human_approved", "agent": "hermes-ops-cfo"},
        )
        target["status"] = "APPROVED_HUMAN"
        target["payment_link"] = link["url"]
        target["decision"] = "Human approved after CFO gate"
        state["audit_trail"].append(
            {
                "at": now_iso(),
                "type": "human_approval",
                "summary": f"Human approved {target['name']} for ${target['amount_usd']}",
                "url": link["url"],
            }
        )
        self._recompute(state)
        self._save(state)
        return state

    def current_state(self) -> Dict[str, Any]:
        return self._load()

    def reset(self) -> None:
        if self.ledger_path.exists():
            self.ledger_path.unlink()

    def _build_spend_plan(self, goal: str) -> List[Dict[str, Any]]:
        return [
            {
                "name": "Brand kit / logo SaaS",
                "amount_usd": 12,
                "category": "marketing",
                "reason": "Fast visual identity for the offer page and demo thumbnail",
                "attacker_no_business_noise": "Revenue-enabling spend",
            },
            {
                "name": "Email outreach tool",
                "amount_usd": 30,
                "category": "sales",
                "reason": "Reach first customer leads without manual spreadsheet work",
                "attacker_no_business_noise": "Customer acquisition spend",
            },
            {
                "name": "GPU inference credits",
                "amount_usd": 200,
                "category": "delivery",
                "reason": "Burst compute for repo triage and report generation",
                "attacker_no_business_noise": "Delivery capacity spend; large enough to require approval",
            },
        ]

    def _build_ops_plan(self) -> List[Dict[str, str]]:
        return [
            {"status": "DONE", "task": "Draft landing page promise and $499 offer"},
            {"status": "DONE", "task": "Create Stripe customer payment link"},
            {"status": "DONE", "task": "Prepare customer intake checklist"},
            {"status": "DONE", "task": "Gate vendor spend by budget and approval threshold"},
            {"status": "READY", "task": "Record 1-3 minute hackathon demo"},
        ]

    def _recompute(self, state: Dict[str, Any]) -> None:
        items = state["spend"]["items"]
        approved_total = sum(item["amount_usd"] for item in items if item["status"].startswith("APPROVED"))
        blocked_total = sum(item["amount_usd"] for item in items if item["status"].startswith("BLOCKED"))
        revenue = state["revenue"]["amount_usd"]
        margin = revenue - approved_total
        state["spend"]["approved_total_usd"] = approved_total
        state["spend"]["blocked_total_usd"] = blocked_total
        state["spend"]["remaining_budget_usd"] = state["budget_usd"] - approved_total
        state["unit_economics"] = {
            "revenue_potential_usd": revenue,
            "approved_spend_usd": approved_total,
            "projected_margin_usd": margin,
            "gross_margin_percent": round((margin / revenue) * 100, 2),
            "blocked_spend_pending_approval_usd": blocked_total,
        }

    def _save(self, state: Dict[str, Any]) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    def _load(self) -> Dict[str, Any]:
        if not self.ledger_path.exists():
            return {}
        return json.loads(self.ledger_path.read_text())
