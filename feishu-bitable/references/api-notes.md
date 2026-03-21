# Feishu Bitable API Notes

Base host:

```text
https://open.feishu.cn
```

Common endpoints:

- `POST /open-apis/auth/v3/tenant_access_token/internal`
- `GET /open-apis/bitable/v1/apps/{app_token}/tables`
- `GET /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/fields`
- `POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/search`
- `PUT /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/{record_id}`

Common environment variables:

- `FEISHU_APP_ID`
- `FEISHU_APP_SECRET`
- `FEISHU_TENANT_ACCESS_TOKEN`

Common response contract:

- `code == 0` means success
- `msg` contains the server-side error summary
- `data` contains the response body

Field write reminder:

- Text and number fields are simple values.
- Complex fields require Feishu-specific JSON structures.
- Always inspect fields before writing to avoid schema mismatch errors.
