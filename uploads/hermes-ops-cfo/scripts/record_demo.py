from __future__ import annotations

import asyncio
import json
import subprocess
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "demo_artifacts"
BASE_URL = "http://127.0.0.1:8765"


def post_json(path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        BASE_URL + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        return json.loads(res.read().decode("utf-8"))


async def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    for old in OUT_DIR.glob("frame_*.png"):
        old.unlink()
    post_json("/api/reset", {})
    segments: list[tuple[Path, float]] = []
    frame_no = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            executable_path="/usr/bin/google-chrome",
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(viewport={"width": 1280, "height": 720})
        page = await context.new_page()
        await page.goto(BASE_URL, wait_until="networkidle")
        await page.add_style_tag(content="""
          #demo-caption { position: fixed; left: 28px; bottom: 24px; right: 28px; z-index: 99999; padding: 18px 22px; border-radius: 18px; background: rgba(4, 8, 15, .88); border: 1px solid rgba(99,168,255,.55); color: #eef5ff; font: 700 30px/1.25 Inter, system-ui, sans-serif; box-shadow: 0 24px 80px rgba(0,0,0,.45); backdrop-filter: blur(12px); }
          #demo-cursor { position: fixed; left: 50px; top: 50px; width: 24px; height: 24px; border: 3px solid #ffffff; border-radius: 999px; z-index: 100000; pointer-events: none; box-shadow: 0 0 0 7px rgba(98,168,255,.28), 0 0 28px rgba(98,168,255,.8); transition: left .3s ease, top .3s ease, transform .14s ease; }
          .demo-pulse { animation: demoPulse 1.2s ease-in-out infinite alternate; }
          @keyframes demoPulse { from { box-shadow: 0 0 0 0 rgba(49,208,127,.55); } to { box-shadow: 0 0 0 11px rgba(49,208,127,0); } }
        """)
        await page.evaluate("""
          () => {
            const caption = document.createElement('div');
            caption.id = 'demo-caption';
            caption.textContent = 'Hermes Ops CFO: an agent that can earn, spend, and govern business operations.';
            document.body.appendChild(caption);
            const cursor = document.createElement('div');
            cursor.id = 'demo-cursor';
            document.body.appendChild(cursor);
          }
        """)

        async def snap(seconds: float) -> None:
            nonlocal frame_no
            frame_no += 1
            path = OUT_DIR / f"frame_{frame_no:03d}.png"
            await page.screenshot(path=str(path), full_page=False)
            segments.append((path, seconds))

        async def caption(text: str, seconds: float) -> None:
            await page.evaluate("text => document.getElementById('demo-caption').textContent = text", text)
            await page.wait_for_timeout(250)
            await snap(seconds)

        async def move_to(locator) -> None:
            box = await locator.bounding_box()
            if not box:
                return
            x = box["x"] + box["width"] / 2
            y = box["y"] + box["height"] / 2
            await page.evaluate(
                "([x,y]) => { const c=document.getElementById('demo-cursor'); c.style.left=x+'px'; c.style.top=y+'px'; }",
                [x, y],
            )
            await page.wait_for_timeout(350)

        async def click(locator) -> None:
            await move_to(locator)
            await page.evaluate("() => document.getElementById('demo-cursor').style.transform='scale(.72)'")
            await page.wait_for_timeout(150)
            await locator.click()
            await page.evaluate("() => document.getElementById('demo-cursor').style.transform='scale(1)'")
            await page.wait_for_timeout(700)

        await caption("Hermes Ops CFO: an agent that can earn, spend, and govern business operations.", 4.0)
        await move_to(page.locator("#goal"))
        await caption("Goal: launch a paid AI security review business with a $250 operations budget.", 5.0)
        await caption("The agent starts from a business goal, not a chatbot toy prompt.", 4.2)
        await click(page.get_by_role("button", name="Forge Ops Plan"))
        await caption("Click Forge Ops Plan: the agent creates revenue, spend plan, budget gate, and audit trail.", 5.4)
        await page.locator("#revenue").evaluate("el => el.parentElement.classList.add('demo-pulse')")
        await caption("Revenue potential: $499 via a Stripe-style customer payment link.", 5.0)
        await page.locator("#spend").evaluate("el => el.parentElement.classList.add('demo-pulse')")
        await caption("Safe vendor spend is auto-approved: $12 brand kit plus $30 outreach tool = $42.", 5.3)
        await page.locator("#margin").evaluate("el => el.parentElement.classList.add('demo-pulse')")
        await caption("Projected margin before large approvals: $457. Business value is visible immediately.", 5.0)
        await page.locator("#blocked").evaluate("el => el.parentElement.classList.add('demo-pulse')")
        await caption("Large spend is not blindly executed: $200 GPU credits are blocked for approval.", 5.6)
        approve = page.get_by_role("button", name="Approve")
        await move_to(approve)
        await caption("Human approval is explicit. The agent can request spend, but it cannot silently blow the budget.", 5.2)
        await click(approve)
        await caption("After approval: approved spend becomes $242, blocked spend becomes $0, margin becomes $257.", 5.5)
        await caption("Every decision is auditable: revenue link, auto-approved spend, approval gate, human approval.", 5.5)
        await page.mouse.wheel(0, 520)
        await page.wait_for_timeout(400)
        await caption("Safe payment semantics: no key required for demo; Stripe test keys work; live keys are refused.", 5.2)
        await caption("Hackathon thesis: agents that earn, spend, and run real operations with guardrails.", 5.2)
        await page.screenshot(path=str(OUT_DIR / "ops-cfo-final-frame.png"), full_page=False)
        await caption("Hermes Ops CFO — working local prototype, API, dashboard, tests, and audit ledger.", 5.8)

        await context.close()
        await browser.close()

    concat = OUT_DIR / "frames.txt"
    with concat.open("w") as f:
        for path, duration in segments:
            f.write(f"file '{path.as_posix()}'\n")
            f.write(f"duration {duration}\n")
        # concat demuxer needs final file repeated to honor the last duration.
        f.write(f"file '{segments[-1][0].as_posix()}'\n")

    mp4_path = OUT_DIR / "hermes-ops-cfo-demo.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat),
            "-vf",
            "fps=30,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "22",
            "-movflags",
            "+faststart",
            "-an",
            str(mp4_path),
        ],
        check=True,
    )
    print(mp4_path)


if __name__ == "__main__":
    asyncio.run(main())
