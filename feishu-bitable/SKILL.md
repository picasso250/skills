---
name: feishu-bitable
description: Fetch Feishu tenant access tokens and read or update Feishu Bitable data with reusable Python scripts. Use when working with Feishu multi-dimensional tables, including listing tables or fields, reading records, and updating records through the official Open Platform APIs.
---

# Feishu Bitable

Use the bundled scripts to talk to Feishu Open Platform without rewriting request code each time.

## Quick Start

Set credentials with environment variables or pass them as CLI flags:

```powershell
$env:FEISHU_APP_ID="cli_xxx"
$env:FEISHU_APP_SECRET="xxx"
```

Fetch a tenant access token:

```powershell
python .\scripts\get_tenant_access_token.py
```

Inspect a base:

```powershell
python .\scripts\list_tables.py --app-token bascnxxxxxxxx
python .\scripts\list_fields.py --app-token bascnxxxxxxxx --table-id tblxxxxxxxx
python .\scripts\list_records.py --app-token bascnxxxxxxxx --table-id tblxxxxxxxx
```

Update one record:

```powershell
python .\scripts\update_record.py --app-token bascnxxxxxxxx --table-id tblxxxxxxxx --record-id recxxxxxxxx --fields-json '{"Status":"Done"}'
```

## Workflow

1. Run `scripts/get_tenant_access_token.py` to confirm the app credentials work.
2. Run `scripts/list_tables.py` to find the target `table_id`.
3. Run `scripts/list_fields.py` to inspect field names and types before writing.
4. Run `scripts/list_records.py` to verify the current row data.
5. Run `scripts/update_record.py` or extend the helper in `scripts/feishu_api.py` for more operations.

## Notes

- Prefer environment variables for secrets; do not hardcode credentials in scripts.
- The scripts search for `.env` upward from the script directory. If `FEISHU_APP_ID` or `FEISHU_APP_SECRET` is still missing, they open a small Tk window with the Feishu Open Platform link and prompt for the two values.
- `app_token` is the Bitable app token, not the application `app_id`.
- Field payloads must match Feishu field schemas. Read field metadata before writing complex types such as people, attachments, or linked records.
- If the API returns permission errors, verify both Open Platform scopes and the Bitable sharing permissions.

## Resources

### scripts/

- `feishu_api.py`: shared HTTP helpers and auth handling
- `get_tenant_access_token.py`: fetch token from `app_id` and `app_secret`
- `list_tables.py`: list Bitable tables
- `list_fields.py`: list field metadata in one table
- `list_records.py`: list or search records
- `update_record.py`: update one record with JSON field data

### references/

- `api-notes.md`: concise endpoint list and payload reminders
