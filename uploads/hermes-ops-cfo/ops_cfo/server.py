from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict

from .engine import OpsCFOAgent, StripeGateway

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "static"
DEFAULT_LEDGER = ROOT / "ledger.json"


def make_agent(ledger_path: Path = DEFAULT_LEDGER) -> OpsCFOAgent:
    return OpsCFOAgent(stripe=StripeGateway.from_env(), ledger_path=ledger_path)


class OpsCFOHandler(BaseHTTPRequestHandler):
    server_version = "HermesOpsCFO/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        if self.path in ("/", "/index.html"):
            self._send_bytes((STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            return
        if self.path == "/api/health":
            self._send_json({"ok": True, "app": "Hermes Ops CFO"})
            return
        if self.path == "/api/state":
            self._send_json(self.server.agent.current_state())  # type: ignore[attr-defined]
            return
        self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        try:
            if self.path == "/api/run-demo":
                payload = self._read_json()
                state = self.server.agent.run_goal(  # type: ignore[attr-defined]
                    goal=payload.get("goal", "Launch paid AI security review service"),
                    budget_usd=int(payload.get("budget_usd", 250)),
                    customer_offer_usd=int(payload.get("customer_offer_usd", 499)),
                )
                self._send_json(state)
                return
            if self.path == "/api/approve":
                payload = self._read_json()
                state = self.server.agent.approve_spend(payload.get("name", ""))  # type: ignore[attr-defined]
                self._send_json(state)
                return
            if self.path == "/api/reset":
                self.server.agent.reset()  # type: ignore[attr-defined]
                self._send_json({"ok": True, "state": {}})
                return
            self.send_error(404, "Not found")
        except Exception as exc:  # demo server: return explicit JSON errors
            self._send_json({"ok": False, "error": str(exc)}, status=400)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[ops-cfo] {self.address_string()} {format % args}")

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("content-length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        self._send_bytes(json.dumps(payload, indent=2).encode("utf-8"), "application/json", status)

    def _send_bytes(self, payload: bytes, content_type: str, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)


class OpsCFOServer(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int], agent: OpsCFOAgent):
        super().__init__(address, OpsCFOHandler)
        self.agent = agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Hermes Ops CFO hackathon demo server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = parser.parse_args()

    server = OpsCFOServer((args.host, args.port), make_agent(args.ledger))
    print(f"Hermes Ops CFO running: http://{args.host}:{args.port}")
    print(f"Ledger: {args.ledger}")
    server.serve_forever()


if __name__ == "__main__":
    main()
