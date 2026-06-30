# Project backlog

Editor-captured ideas for what to work on next. When asked what is left to do, suggest from this list (and cross-check against current repo state — some items may be partially done).

## Backlog

1. **Architecture and coding-style hygiene** — Improve docs around consistency, completeness of features, and keeping architecture docs in sync with the code (reduce drift).

2. **DRY and simplify** — Make the codebase DRYer: reduce duplication and complexity in both implementation and the preprocessing workflow.

3. **Reader web app** — Build the full reader web application (consumes packaged local content; no LLM at runtime).

4. **Document / PDF exporter** — Export curated documents (e.g. PDF or similar) from packaged content.

5. **Preprocessor CI** — Continuous integration for the preprocessing pipeline (validation, tests, and/or artifact checks in CI).

6. **Automated context note annotation** — Automate context-note drafting with a higher-quality model (today context notes are skill/CLI-driven with stubbed annotate/review commands).
