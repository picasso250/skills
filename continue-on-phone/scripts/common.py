from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import requests


SCRIPT_DIR = Path(__file__).resolve().parent
STATE_DIR = Path.home() / ".continue-on-phone"
STATE_DIR.mkdir(parents=True, exist_ok=True)
ACTIVE_SESSION_PATH = STATE_DIR / "active_session.json"
DEFAULT_BASE_URL = "https://cop.io99.xyz"


def configure_stdio_utf8() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except Exception:
                pass


def require_base_url() -> str:
    value = os.environ.get("CONTINUE_ON_PHONE_BASE_URL", "").strip().rstrip("/")
    if value:
        return value
    return DEFAULT_BASE_URL


def state_path_for(session_id: str) -> Path:
    return STATE_DIR / f"{session_id}.json"


def load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def save_json_file(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_active_session() -> str | None:
    data = load_json_file(ACTIVE_SESSION_PATH, {})
    return data.get("session_id")


def save_active_session(session_id: str, session_url: str, app_token: str) -> None:
    save_json_file(
        ACTIVE_SESSION_PATH,
        {
          "session_id": session_id,
          "session_url": session_url,
          "app_token": app_token,
        },
    )


def load_session_state(session_id: str) -> dict[str, Any]:
    return load_json_file(
        state_path_for(session_id),
        {
            "session_id": session_id,
            "app_token": None,
            "last_user_ts": None,
        },
    )


def save_session_state(session_id: str, data: dict[str, Any]) -> None:
    save_json_file(state_path_for(session_id), data)


def build_cookie_header(session_id: str, app_token: str) -> str:
    return f"cop_session_id={session_id}; cop_session_token={app_token}"


def make_request_headers(session_id: str | None = None, app_token: str | None = None) -> dict[str, str]:
    headers: dict[str, str] = {}
    if session_id and app_token:
        headers["Cookie"] = build_cookie_header(session_id, app_token)
    return headers


def api_post(
    path: str,
    payload: dict[str, Any],
    *,
    session_id: str | None = None,
    app_token: str | None = None,
) -> dict[str, Any]:
    base_url = require_base_url()
    response = requests.post(
        f"{base_url}{path}",
        json=payload,
        headers=make_request_headers(session_id, app_token),
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def api_get(
    path: str,
    params: dict[str, Any] | None = None,
    *,
    session_id: str | None = None,
    app_token: str | None = None,
) -> dict[str, Any]:
    base_url = require_base_url()
    response = requests.get(
        f"{base_url}{path}",
        params=params,
        headers=make_request_headers(session_id, app_token),
        timeout=35,
    )
    response.raise_for_status()
    return response.json()
