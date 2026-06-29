# Hermes Ops CFO

Hermes Ops CFO is an autonomous business-operations agent built for the
**Hermes Agent Accelerated Business Hackathon**.

This repository exists to show a governed agentic business operator: an agent
that can earn, spend, run operational workflows, track margin, and leave an
audit trail. The core idea is not another chatbot - it is a business operator
with revenue, spend controls, margin tracking, human approval gates, and
auditability.

## Purpose

Given a high-level business goal and budget, Hermes Ops CFO can:

- Create a revenue offer.
- Generate a Stripe-style customer payment link.
- Plan vendor spend.
- Auto-approve low-risk purchases.
- Block larger spend behind human approval.
- Compute projected margin.
- Write every revenue, spend, approval, and refusal decision to an auditable ledger.

The project is intentionally small and local-first so the safety model is easy
to inspect. It is meant as a hackathon proof of concept for agent-run business
operations, not as a production finance system.

## Demo Scenario

For the demo scenario, Hermes Ops CFO launches a paid AI security review service
with a `$250` budget.

It creates a `$499` customer revenue link, approves `$42` in safe vendor spend,
blocks `$200` in GPU inference credits until human approval, and updates
projected margin from `$457` to `$257` after approval.

## What Is Included

- Public-facing Hermes website in `Hermes.dc.html`.
- Local dashboard for the Ops CFO demo.
- Stdlib API server.
- CLI demo.
- Behavior tests.
- Sample ledger.
- Recorded demo video and supporting artifacts.

The runnable agent project lives in:

```text
uploads/hermes-ops-cfo/
```

## Bring Your Own Skills

This repo provides the agent scaffold, safety boundaries, and demo workflow.
To use it for a real business scenario, you still need to bring your own
operator skills:

- Define the actual business goal, offer, budget, and approval policy.
- Decide which vendor spend is low-risk versus approval-required.
- Review the generated ledger and financial assumptions.
- Supply your own Stripe test key if you want real Stripe test-mode Payment
  Link objects.
- Adapt the workflow to your own domain knowledge, compliance needs, and risk
  tolerance.

The agent is designed to make those decisions explicit and auditable. It does
not remove human accountability; it gives the human a governed operating loop.

## Safety Model

By default, Hermes Ops CFO runs in safe deterministic demo mode with no secrets
required. It returns stable `stripe.test` links and creates no external payment
side effects.

If `STRIPE_SECRET_KEY=sk_test_...` is provided, the agent can create real
Stripe test-mode Product, Price, and Payment Link objects. Live Stripe keys are
refused by design.

Local runtime state such as `ledger.json`, `.env` files, private keys, logs,
and caches are ignored by Git.

## Quick Start

```bash
cd uploads/hermes-ops-cfo
python3 -m ops_cfo.server --port 8765
```

Open:

```text
http://127.0.0.1:8765
```

CLI one-shot:

```bash
python3 -m ops_cfo.demo_cli --goal "Launch paid AI security review service" --budget 250 --offer 499
```

Tests:

```bash
python3 -m unittest discover -s tests -v
```

## Hackathon Thesis

Autonomous agents become more interesting when they touch real business
operations: revenue, spending, approval gates, margin, and auditability.
Hermes Ops CFO is a compact demonstration of that idea.
