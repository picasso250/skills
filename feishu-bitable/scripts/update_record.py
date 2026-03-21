import argparse
import json

from feishu_api import dump_json, env_or_value, request_json, require_value, resolve_tenant_access_token


def main() -> int:
    parser = argparse.ArgumentParser(description="Update one Feishu Bitable record")
    parser.add_argument("--app-token", help="Bitable app token, defaults to FEISHU_BITABLE_APP_TOKEN")
    parser.add_argument("--table-id", help="Defaults to FEISHU_BITABLE_TABLE_ID")
    parser.add_argument("--record-id", required=True)
    parser.add_argument("--fields-json", required=True, help="JSON object for fields")
    parser.add_argument("--tenant-access-token", help="Defaults to FEISHU_TENANT_ACCESS_TOKEN")
    args = parser.parse_args()

    app_token = require_value(env_or_value(args.app_token, "FEISHU_BITABLE_APP_TOKEN"), "app token")
    table_id = require_value(env_or_value(args.table_id, "FEISHU_BITABLE_TABLE_ID"), "table id")
    tenant_access_token = resolve_tenant_access_token(args.tenant_access_token)

    dump_json(
        request_json(
            "PUT",
            f"/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{args.record_id}",
            token=tenant_access_token,
            body={"fields": json.loads(args.fields_json)},
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
