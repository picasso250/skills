---
name: edit-env-with-tk
description: Update a `.env` file by collecting secret values through local Python Tk dialogs instead of chat. Use when Codex needs to create or modify `.env` files, especially in the home directory, and the user should type API keys, passwords, tokens, or other sensitive values without exposing them to the AI.
---

# Edit Env With Tk

Use `scripts/update_env_with_tk.py` to prompt for one or more values in a local GUI. The prompt masks characters, so the value never needs to be pasted into chat or echoed in terminal logs.

## Workflow

1. Decide which `.env` file to edit.
Default to the user's home directory only when the request implies a home-level config and no project-local `.env` is more appropriate.

2. Decide which keys to update.
Prefer explicit keys from the user's request. If the user names a service but not the exact variable, inspect the repo or existing `.env.example` first.

3. Run the script with only non-secret arguments.
Pass the file path and key names on the command line. Do not pass secret values as CLI flags or environment variables.

```powershell
py scripts/update_env_with_tk.py --file "$HOME\.env" --key OPENAI_API_KEY
py scripts/update_env_with_tk.py --file ".env" --key OPENAI_API_KEY --key ANTHROPIC_API_KEY
```

4. Let the user type secrets into the Tk window.
The GUI masks input. Existing values are not shown. The script tells the user whether a key already exists so they know whether they are replacing or adding it.

5. Verify only non-secret outcomes.
Confirm that the target file was updated and which keys changed. Do not print values back to the user unless they explicitly ask and the risk is acceptable.

## Notes

- Preserve unrelated lines, comments, and ordering in the `.env` file.
- Create the file if it does not exist.
- Write a backup file named like `.env.YYYY-mm-dd-hh-mm-ss.bak` before modifying an existing `.env`.
- Write values as double-quoted `.env` strings with escaping for backslashes, quotes, and newlines.
- Abort without writing if the user cancels the dialog.
- Prefer this skill over asking the user to paste secrets into chat.
