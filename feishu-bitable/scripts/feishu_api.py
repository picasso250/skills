import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = "https://open.feishu.cn"
_DOTENV_LOADED = False


class FeishuAPIError(RuntimeError):
    pass


def load_dotenv() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return

    current = Path(__file__).resolve()
    for directory in [current.parent, *current.parents]:
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

    app_id = require_value(env_or_value(None, "FEISHU_APP_ID"), "app id")
    app_secret = require_value(env_or_value(None, "FEISHU_APP_SECRET"), "app secret")
    response = get_tenant_access_token(app_id, app_secret)
    return require_value(response.get("tenant_access_token"), "tenant access token")
