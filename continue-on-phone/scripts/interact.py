from __future__ import annotations

import argparse
import sys
import time

from common import (
    api_get,
    api_post,
    configure_stdio_utf8,
    load_active_session,
    load_session_state,
    save_session_state,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Append an agent message into the active continue-on-phone session, then wait for new user replies."
    )
    parser.add_argument("--text", required=True, help="Text to append as the agent message.")
    parser.add_argument("--session-id", help="Override the active session id.")
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=30,
        help="How long to wait before reading new user messages. Default: 30.",
    )
    return parser


def print_messages(messages: list[dict]) -> None:
    if not messages:
        return
    for message in messages:
        print(f"[{message['ts']}] {message['role']}: {message['text']}")


def main() -> None:
    configure_stdio_utf8()
    args = build_parser().parse_args()
    session_id = args.session_id or load_active_session()
    if not session_id:
        raise SystemExit("No active session. Run start_scan.py first or pass --session-id.")

    api_post(
        f"/api/sessions/{session_id}/messages",
        {
            "role": "agent",
            "text": args.text,
        },
    )

    state = load_session_state(session_id)
    last_user_ts = state.get("last_user_ts")

    time.sleep(max(args.wait_seconds, 0))

    params = {"role": "user"}
    if last_user_ts:
        params["since"] = last_user_ts

    result = api_get(f"/api/sessions/{session_id}/messages", params=params)
    messages = result.get("messages", [])

    if messages:
        print_messages(messages)
        newest_ts = messages[-1]["ts"]
        state["last_user_ts"] = newest_ts
        save_session_state(session_id, state)
        return

    print("No new user messages.")
    if last_user_ts is None:
        session = api_get(f"/api/sessions/{session_id}")
        user_messages = [message for message in session.get("messages", []) if message.get("role") == "user"]
        if user_messages:
            state["last_user_ts"] = user_messages[-1]["ts"]
            save_session_state(session_id, state)
    sys.exit(0)


if __name__ == "__main__":
    main()
