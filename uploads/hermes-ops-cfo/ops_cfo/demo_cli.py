from __future__ import annotations

import argparse
import json
from pathlib import Path

from .engine import OpsCFOAgent, StripeGateway


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Hermes Ops CFO once and print the CFO ledger")
    parser.add_argument("--goal", default="Launch paid AI security review service")
    parser.add_argument("--budget", type=int, default=250)
    parser.add_argument("--offer", type=int, default=499)
    parser.add_argument("--ledger", type=Path, default=Path("ledger.json"))
    args = parser.parse_args()

    agent = OpsCFOAgent(stripe=StripeGateway.from_env(), ledger_path=args.ledger)
    state = agent.run_goal(args.goal, args.budget, args.offer)
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
