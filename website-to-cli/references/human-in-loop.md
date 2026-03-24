# Human-In-The-Loop Guide for Website To Cli

## Before each transformation
- Ask the user to restate the page, button, or field the CLI step should touch.
- Collect the precise selectors, timing expectations, and success criteria that they are watching.
- Verbally describe the automation you plan to add and confirm: “Is this what you expect the CLI to do next?”

## Sample check-in prompts
1. “I see the workflow hits `<selector>` and then waits for `<event>`. Should that become CLI step 2?”
2. “Do you want this argument to accept a literal value, or should the CLI re‑compute it (token, timestamp, ID)?”
3. “Can you show me the success output you would consider deterministically equivalent to the browser action?”
4. “If this step fails, do you want a human prompt, a retry, or a bail-out message in the CLI?”

## Logging confirmations
- Keep a running list of (step label, approved by, notes) so future agents know which actions were signed off and why.
- Capture assumptions that changed during the flow, explicitly tagging them as “needs review” or “explained to the user.”
- Save any hand-off instructions (required env vars, startup commands, remote debugging tips) alongside the final CLI.
