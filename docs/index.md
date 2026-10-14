# Wenyan Reader Docs

Living reference for the product, its contracts, and its implementation. Pages describe the repo as it is today; planned work lives in the [backlog](backlog.md).

## Product — what and why

- [Overview](product/overview.md) — what the product is, principles, content model
- [Editor Guide](product/editor-guide.md) — taking a document from source to reader package
- [Reader UX](product/reader-ux.md) — intended reading experience (not built)

## Spec — contracts and behavior

- [Pipeline](spec/pipeline.md) — stages, scope, and who decides (LLM, code, editor + agent)
- [CLI](spec/cli.md) — commands, options, output, exit codes
- [Artifacts](spec/artifacts.md) — preprocessing files, input hashes, effective status
- [Quality Gates](spec/quality-gates.md) — deterministic checks, reviews, blocking
- [Reader Package](spec/reader-package.md) — files the reader consumes

## Architecture — how it is built

- [Overview](architecture/overview.md) — stack, packages, layout, configuration
- [Jobs and LLM](architecture/jobs-and-llm.md) — job runner, prompts, LLM clients, retries
- [Coding Style](architecture/coding-style.md) — layering, Pydantic, typing rules
- [Web App](architecture/webapp.md) — open decisions

## Planning

- [Backlog](backlog.md) — features and known gaps
- [Proposals](proposals/) — detailed designs not yet built
- [Glossary](glossary.md) — vocabulary

## Conventions

- Each page opens with its type: **Product**, **Spec**, **Guide**, or **Architecture**.
- Spec pages describe observable behavior and never reference code modules except model packages. Architecture pages describe code and link to specs for behavior.
- Specs describe what exists. Unbuilt behavior goes to the backlog; detailed designs go to `proposals/` with a status line.
- Define each term once in the [glossary](glossary.md) and link to it.
- When code changes behavior, update the matching spec in the same change.
