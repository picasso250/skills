import argparse

from feishu_api import dump_json, env_or_value, get_tenant_access_token, require_value


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Feishu tenant_access_token")
    parser.add_argument("--app-id", help="Feishu app id, defaults to FEISHU_APP_ID")
    parser.add_argument("--app-secret", help="Feishu app secret, defaults to FEISHU_APP_SECRET")
    args = parser.parse_args()

    app_id = require_value(env_or_value(args.app_id, "FEISHU_APP_ID"), "app id")
    app_secret = require_value(env_or_value(args.app_secret, "FEISHU_APP_SECRET"), "app secret")
    dump_json(get_tenant_access_token(app_id, app_secret))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
