"""HTTP and command-line entry points for the Party City voice demo."""

from __future__ import annotations

import argparse
import json
import signal
from typing import Any

from flask import Flask, jsonify, request

from automation import AutomationError, PartyCityAutomation, automation_from_environment


SUPPORTED_ITEMS = ("balloon", "pinata")
PREFERRED_TARGET_KEYS = ("item", "new_item", "newItem", "target", "to", "replacement")

app = Flask(__name__)
automation: PartyCityAutomation | None = None


def item_from_payload(payload: Any) -> str | None:
    """Extract the requested end state from an otherwise arbitrary AR payload."""
    if isinstance(payload, dict):
        for key in PREFERRED_TARGET_KEYS:
            if key in payload:
                target = item_from_payload(payload[key])
                if target is not None:
                    return target

    text = (
        payload
        if isinstance(payload, str)
        else json.dumps(payload, ensure_ascii=False, default=str)
    ).lower()
    text = text.replace("piñata", "pinata").replace("pinate", "pinata")

    # If a transcript mentions both old and new products, the last mention is
    # normally the requested replacement ("change balloon to pinata").
    matches = [
        (text.rfind("balloon"), "balloon"),
        (text.rfind("pinata"), "pinata"),
    ]
    position, item = max(matches)
    return item if position >= 0 else None


def get_automation() -> PartyCityAutomation:
    if automation is None:
        raise AutomationError("Browser automation is not running.")
    return automation


@app.get("/health")
def health() -> tuple[Any, int]:
    return jsonify({"ok": True, "browser_started": automation is not None}), 200


@app.post("/change")
def change_item() -> tuple[Any, int]:
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"ok": False, "error": "Send a JSON request body."}), 400

    item = item_from_payload(payload)
    if item is None:
        return (
            jsonify(
                {
                    "ok": False,
                    "error": "JSON must request either 'balloon' or 'pinata'.",
                }
            ),
            400,
        )

    try:
        result = get_automation().handle_change(item)
    except (AutomationError, ValueError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500

    return jsonify({"ok": True, **result.as_dict()}), 200


def run_server(host: str, port: int) -> None:
    global automation
    automation = automation_from_environment()
    automation.start_browser()

    def close_browser(*_: object) -> None:
        if automation is not None:
            automation.close()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, close_browser)
    signal.signal(signal.SIGTERM, close_browser)
    # Playwright's sync API must be called on the thread where it was created.
    app.run(host=host, port=port, threaded=False, use_reloader=False)


def run_one_command(item: str) -> None:
    browser_automation = automation_from_environment()
    try:
        result = browser_automation.handle_change(item)
        print(json.dumps({"ok": True, **result.as_dict()}, indent=2))
        input("Browser will stay open. Press Enter to close it...")
    finally:
        browser_automation.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "item",
        nargs="?",
        choices=SUPPORTED_ITEMS,
        help="Run one command directly instead of starting the API.",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.item:
        run_one_command(args.item)
    else:
        run_server(args.host, args.port)
