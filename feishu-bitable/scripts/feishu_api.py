import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path


BASE_URL = "https://open.feishu.cn"
_DOTENV_LOADED = False


class FeishuAPIError(RuntimeError):
    pass


def load_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return

    candidates = []
    script_path = Path(__file__).resolve()
    candidates.extend([script_path.parent, *script_path.parents])

    try:
        cwd_path = Path.cwd().resolve()
        candidates.extend([cwd_path, *cwd_path.parents])
    except Exception:
        pass

    home_path = Path.home().resolve()
    candidates.extend([home_path])

    seen = set()
    for directory in candidates:
        normalized = str(directory)
        if normalized in seen:
            continue
        seen.add(normalized)
        env_path = directory / ".env"
        if not env_path.is_file():
            continue

        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value
        break

    _DOTENV_LOADED = True


def env_or_value(value: str | None, env_name: str) -> str | None:
    load_dotenv()
    if value:
        return value
    return os.getenv(env_name)


def require_value(value: str | None, label: str) -> str:
    if value:
        return value
    raise FeishuAPIError(f"missing {label}")


def prompt_for_app_credentials() -> tuple[str, str]:
    open_platform_url = "https://open.feishu.cn/"
    message = (
        "Missing FEISHU_APP_ID / FEISHU_APP_SECRET.\n"
        "Open Feishu Open Platform, enter the App ID and App Secret for your app,\n"
        "then submit to continue.\n"
        f"URL: {open_platform_url}"
    )

    try:
        import tkinter as tk
        from tkinter import messagebox
    except Exception as exc:
        raise FeishuAPIError(
            "missing app id/app secret. Open https://open.feishu.cn/ and set FEISHU_APP_ID / FEISHU_APP_SECRET."
        ) from exc

    result = {"app_id": "", "app_secret": ""}

    root = tk.Tk()
    root.title("Feishu Credentials")
    root.resizable(False, False)
    root.attributes("-topmost", True)

    frame = tk.Frame(root, padx=16, pady=16)
    frame.pack(fill="both", expand=True)

    tk.Label(frame, text="Missing Feishu app credentials.", anchor="w", justify="left").pack(fill="x")
    tk.Label(frame, text="Get App ID and App Secret from Feishu Open Platform.", anchor="w", justify="left").pack(fill="x")

    link_var = tk.StringVar(value=open_platform_url)
    link_entry = tk.Entry(frame, textvariable=link_var, state="readonly", width=48, readonlybackground="white")
    link_entry.pack(fill="x", pady=(8, 4))

    def open_link() -> None:
        webbrowser.open(open_platform_url)

    tk.Button(frame, text="Open Feishu Open Platform", command=open_link).pack(anchor="w", pady=(0, 12))

    tk.Label(frame, text="App ID", anchor="w").pack(fill="x")
    app_id_entry = tk.Entry(frame, width=48)
    app_id_entry.pack(fill="x", pady=(0, 8))

    tk.Label(frame, text="App Secret", anchor="w").pack(fill="x")
    app_secret_entry = tk.Entry(frame, show="*", width=48)
    app_secret_entry.pack(fill="x", pady=(0, 12))

    def submit() -> None:
        app_id = app_id_entry.get().strip()
        app_secret = app_secret_entry.get().strip()
        if not app_id or not app_secret:
            messagebox.showerror("Missing fields", "Enter both App ID and App Secret.")
            return
        result["app_id"] = app_id
        result["app_secret"] = app_secret
        root.destroy()

    def cancel() -> None:
        root.destroy()

    button_row = tk.Frame(frame)
    button_row.pack(fill="x")
    tk.Button(button_row, text="Submit", command=submit).pack(side="left")
    tk.Button(button_row, text="Cancel", command=cancel).pack(side="left", padx=(8, 0))

    app_id_entry.focus_set()
    root.mainloop()

    if not result["app_id"] or not result["app_secret"]:
        raise FeishuAPIError(
            "missing app id/app secret. Open https://open.feishu.cn/ and set FEISHU_APP_ID / FEISHU_APP_SECRET."
        )
    return result["app_id"], result["app_secret"]


def dump_json(data) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def request_json(method: str, path: str, *, token: str | None = None, query: dict | None = None, body: dict | None = None):
    url = BASE_URL + path
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    payload = None
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        payload = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(url=url, data=payload, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        raise FeishuAPIError(f"http {exc.code}: {raw}") from exc
    except urllib.error.URLError as exc:
        raise FeishuAPIError(f"network error: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FeishuAPIError(f"invalid json response: {raw}") from exc

    if data.get("code") not in (None, 0):
        raise FeishuAPIError(f"api error {data.get('code')}: {data.get('msg')}")
    return data


def get_tenant_access_token(app_id: str, app_secret: str) -> dict:
    return request_json(
        "POST",
        "/open-apis/auth/v3/tenant_access_token/internal",
        body={"app_id": app_id, "app_secret": app_secret},
    )


def resolve_tenant_access_token(explicit_token: str | None) -> str:
    token = env_or_value(explicit_token, "FEISHU_TENANT_ACCESS_TOKEN")
    if token:
        return token

    app_id = env_or_value(None, "FEISHU_APP_ID")
    app_secret = env_or_value(None, "FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        app_id, app_secret = prompt_for_app_credentials()
    response = get_tenant_access_token(app_id, app_secret)
    return require_value(response.get("tenant_access_token"), "tenant access token")
