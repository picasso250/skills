import argparse

from feishu_api import dump_json, env_or_value, request_json, require_value, resolve_tenant_access_token


def main() -> int:
    parser = argparse.ArgumentParser(description="List Feishu Bitable field metadata")
    parser.add_argument("--app-token", help="Bitable app token, defaults to FEISHU_BITABLE_APP_TOKEN")
    parser.add_argument("--table-id", help="Defaults to FEISHU_BITABLE_TABLE_ID")
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--page-token")
    parser.add_argument("--tenant-access-token", help="Defaults to FEISHU_TENANT_ACCESS_TOKEN")
    args = parser.parse_args()

    app_token = require_value(env_or_value(args.app_token, "FEISHU_BITABLE_APP_TOKEN"), "app token")
    table_id = require_value(env_or_value(args.table_id, "FEISHU_BITABLE_TABLE_ID"), "table id")
    tenant_access_token = resolve_tenant_access_token(args.tenant_access_token)

    query = {"page_size": args.page_size}
    if args.page_token:
        query["page_token"] = args.page_token

    dump_json(
        request_json(
            "GET",
            f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields",
            token=tenant_access_token,
            query=query,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
