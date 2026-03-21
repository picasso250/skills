---
name: browser-flow-to-cli
description: Use when the user wants to turn a repeatable browser or website interaction flow into a CLI or automation script.
---

# Browser Flow to CLI

## Overview

This skill turns a manual browser workflow into a repeatable CLI workflow.
It is language-agnostic and applies to Python, JavaScript, or any browser automation stack.
When this skill is activated, do the work directly. Do not answer with examples of how to invoke the skill.

## Use When

- The user is describing a browser flow as ordered UI steps.
- The goal is a repeatable local script or CLI, not a one-off manual run.
- The page likely needs selector discovery, hover states, delayed rendering, or download handling.
- The workflow should be tested in the real target environment before writing the final implementation.

## Workflow

### 1. Rewrite the manual flow as a numbered procedure

Example:

1. Open the target URL.
2. Wait at least 5s for the page and network-driven UI to settle.
3. Click the feature entry.
4. Wait 1s.
5. Fill the prompt or form.
6. Wait 1s.
7. Click submit.
8. Wait at least 5s for the output or remote processing to appear.
9. Get the final artifact through the official UI path if possible.

Timing rule:

- Wait at least `5s` for network, page load, remote processing, or async UI updates.
- Use about `1s` only for human-like pacing between visible actions.
- If both apply, use the longer wait.

### 2. Build a small validation implementation first

First write a small validation implementation in the real target environment:
- Log major steps.
- Save screenshots when blocked.
- Print a few useful DOM facts if selectors or result actions are unclear.

Rules:

- The validation implementation is a temporary experiment, not the final deliverable.
- Do not stop after producing the validation implementation.
- Use it to verify selectors, timing, hidden actions, download paths, and real site behavior.

### 3. Prefer stable selectors in this order

Selector priority:

1. `data-testid`
2. Accessible roles and labels
3. Stable text matches
4. Structural CSS selectors

When an action is hidden, hover the relevant container and re-scan for `data-testid`, `download`, `copy`, `save`, or `aria-label`.

### 4. Validate the real completion path

Validate one of:

- A visible result element appears.
- An official download button becomes clickable.
- A copy action becomes available.
- A file download is emitted.
- The output image/file URL is present and usable.

Prefer the official UI download path over scraping preview assets.

### 5. Only then write the production CLI

After the real-environment validation succeeds, write the final implementation.

Write the final implementation with:
- Reused helper logic that survived validation.
- Smaller logs.
- Clear CLI usage.
- A deterministic output contract such as `RESULT_IMAGE_PATH:<path>`.
- Error screenshots only on failure.

## Implementation Pattern

Useful building blocks:

- Reuse the browser context already on the target site when possible.
- Try multiple selector strategies without duplicating control flow.
- Save screenshots only for validation or failure handling.
- Dump a small DOM snapshot only when selectors or result actions are unclear.

## Lessons From Real Usage

- If the flow looks stuck, check for hidden state before assuming failure.
- Hover overlays often hide the real action buttons.
- `data-testid` usually beats guessed text selectors.
- Preview `img.src` may be low resolution; the official download button may return the real asset.

## Output Conventions

Production scripts should print machine-friendly markers:

- `RESULT_IMAGE_PATH:<abs-path>`
- `RESULT_FILE_PATH:<abs-path>`
- `RESULT_JSON:<json>`
