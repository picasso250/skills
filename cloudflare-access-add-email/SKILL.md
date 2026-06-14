---
name: cloudflare-access-add-email
description: Add one email address to the configured Cloudflare Access reusable policy. Use when the user asks to allow, append, add, or whitelist an email for Cloudflare One / Cloudflare Access login.
---

# Cloudflare Access Add Email

Run the bundled PowerShell script:

```powershell
pwsh .\scripts\add-access-email.ps1 -Email user@example.com
```

Defaults:

- Account: `7cd361e713a3e8c115f613ec88a5707f`
- Policy: `Allow my emails` (`eb22d018-3632-46f9-a932-5adcfa8a513b`)
- Token source: `~\.cf\config.toml`

The script is idempotent: it does not add duplicates.
