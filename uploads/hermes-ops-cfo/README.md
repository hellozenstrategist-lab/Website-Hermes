# Hermes Ops CFO

A hackathon prototype for the **Hermes Agent Accelerated Business Hackathon**: a local Hermes-style CFO agent that can earn, spend, block unsafe spend, and leave an auditable business ledger.

## What it demonstrates

- **Earn:** creates a customer Stripe payment link for a `$499 AI Security Review` offer.
- **Spend:** creates vendor-spend payment links for low-risk purchases.
- **Govern:** blocks spend above the auto-approval cap and refuses approvals that exceed the budget.
- **Audit:** writes every revenue/spend/approval decision to `ledger.json`.
- **Safe demo mode:** no Stripe key required; deterministic demo links are used by default.
- **Stripe test mode:** set `STRIPE_SECRET_KEY=sk_test_...` to create real Stripe test-mode Product/Price/Payment Link objects. Live keys are refused.

## Quick start

```bash
cd hermes-ops-cfo
python3 -m ops_cfo.server --port 8765
# open http://127.0.0.1:8765
```

CLI one-shot:

```bash
python3 -m ops_cfo.demo_cli --goal "Launch paid AI security review service" --budget 250 --offer 499
```

Tests:

```bash
python3 -m unittest discover -s tests -v
```

## Demo script, 60 seconds

1. Open the dashboard.
2. Click **Forge Ops Plan**.
3. Show revenue: `$499` Stripe payment link.
4. Show approved spend: `$42`.
5. Show blocked spend: `$200 GPU inference credits` requiring approval.
6. Click approve to show CFO gate can release spend while still staying under budget.
7. Open `ledger.json` to show audit trail.

## Files

```text
ops_cfo/engine.py       CFO agent, Stripe gateway, budget gates
ops_cfo/server.py       stdlib HTTP JSON API + dashboard server
ops_cfo/demo_cli.py     one-shot CLI demo
static/index.html       demo dashboard
tests/                  behavior tests
ledger.json             generated state/audit ledger
```

## API

- `GET /api/health`
- `GET /api/state`
- `POST /api/run-demo` JSON: `{ "goal": "...", "budget_usd": 250, "customer_offer_usd": 499 }`
- `POST /api/approve` JSON: `{ "name": "GPU inference credits" }`
- `POST /api/reset`
