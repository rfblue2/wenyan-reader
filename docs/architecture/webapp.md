# Web App

> **Architecture** — placeholder. The reader web app is not designed or built ([backlog](../backlog.md) F1). UX: [Reader UX](../product/reader-ux.md). Data: [Reader Package](../spec/reader-package.md).

## Constraints

- Reads validated files under `content/` only; no LLM calls.
- Loads large documents incrementally (per paragraph file).
- No local user state; the reading position lives in the URL.
- Content shapes come from `wenyan-models`.

## Decisions to make

| Area | Questions |
|---|---|
| Framework | Simple SPA or filesystem-routed framework? Routing and URL shape for document / chapter / paragraph / segment. |
| Rendering | Clickable token rendering over the segment text. Styling and state management. |
| Content loading | How packages are discovered on disk; build-time vs runtime validation. |
| Shared types | Generated TypeScript from exported JSON Schema, a Python sidecar, or both? |
| Tooling | Package manager, test runner, linter, dev server. |
