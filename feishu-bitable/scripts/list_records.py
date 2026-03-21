import argparse
import json

from feishu_api import dump_json, env_or_value, request_json, require_value, resolve_tenant_access_token


def main() -> int:
    parser = argparse.ArgumentParser(description="Search Feishu Bitable records")
    parser.add_argument("--app-token", help="Bitable app token, defaults to FEISHU_BITABLE_APP_TOKEN")
    parser.add_argument("--table-id", help="Defaults to FEISHU_BITABLE_TABLE_ID")
    parser.add_argument("--page-size", type=int, default=20)
    parser.add_argument("--page-token")
    parser.add_argument("--view-id", help="Defaults to FEISHU_BITABLE_VIEW_ID when omitted")
    parser.add_argument("--filter-json", help="Raw JSON for filter")
    parser.add_argument("--sort-json", help="Raw JSON array for sort rules")
    parser.add_argument("--tenant-access-token", help="Defaults to FEISHU_TENANT_ACCESS_TOKEN")
    args = parser.parse_args()

    app_token = require_value(env_or_value(args.app_token, "FEISHU_BITABLE_APP_TOKEN"), "app token")
    table_id = require_value(env_or_value(args.table_id, "FEISHU_BITABLE_TABLE_ID"), "table id")
    tenant_access_token = resolve_tenant_access_token(args.tenant_access_token)

    body = {
        "page_size": args.page_size,
    }
    if args.page_token:
        body["page_token"] = args.page_token
    view_id = env_or_value(args.view_id, "FEISHU_BITABLE_VIEW_ID")
    if view_id:
        body["view_id"] = view_id
    if args.filter_json:
        body["filter"] = json.loads(args.filter_json)
    if args.sort_json:
        body["sort"] = json.loads(args.sort_json)

    dump_json(
        request_json(
            "POST",
            f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search",
            token=tenant_access_token,
            body=body,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
